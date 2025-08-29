from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction

from apps.surveys.models import (
    Survey, SurveySession, SessionQuestion, Answer, UserSurveyHistory
)
from .serializers import (
    SurveyListSerializer, SurveyDetailSerializer, StartSurveySerializer,
    SurveySessionSerializer, SubmitAnswerSerializer, AnswerSerializer,
    UserSurveyHistorySerializer
)


class SurveyViewSet(ReadOnlyModelViewSet):
    """ViewSet for surveys."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get active surveys."""
        return Survey.objects.filter(is_active=True).order_by('-created_at')
    
    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return SurveyListSerializer
        return SurveyDetailSerializer
    
    def get_serializer_context(self):
        """Add request context to serializer."""
        context = super().get_serializer_context()
        context['language'] = self.request.query_params.get('lang', 'uz')
        return context
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a new survey session."""
        survey = self.get_object()
        
        serializer = StartSurveySerializer(
            data={
                'survey_id': survey.id,
                'questions_count': request.data.get('questions_count'),
                'language': request.data.get('language', 'uz')
            },
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                # Get next attempt number
                last_attempt = SurveySession.objects.filter(
                    user=request.user,
                    survey=survey
                ).order_by('-attempt_number').first()
                
                next_attempt = (last_attempt.attempt_number + 1) if last_attempt else 1
                
                # Create new session
                session = SurveySession.objects.create(
                    user=request.user,
                    survey=survey,
                    attempt_number=next_attempt,
                    language=serializer.validated_data['language'],
                    status='started'
                )
                
                # Initialize questions
                questions_count = serializer.validated_data.get('questions_count')
                session.initialize_questions(questions_count)
                
                # Update session status
                session.status = 'in_progress'
                session.save()
                
                # Update user survey history
                history, created = UserSurveyHistory.objects.get_or_create(
                    user=request.user,
                    survey=survey,
                    defaults={
                        'total_attempts': 1,
                        'current_status': 'in_progress',
                        'last_attempt_at': timezone.now()
                    }
                )
                
                if not created:
                    history.total_attempts += 1
                    history.current_status = 'in_progress'
                    history.last_attempt_at = timezone.now()
                    history.save()
                
                return Response(
                    SurveySessionSerializer(session, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_history(self, request):
        """Get user's survey history."""
        history = UserSurveyHistory.objects.filter(user=request.user).select_related('survey')
        serializer = UserSurveyHistorySerializer(history, many=True)
        return Response(serializer.data)


class SurveySessionViewSet(GenericViewSet):
    """ViewSet for survey sessions."""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SurveySessionSerializer
    
    def get_queryset(self):
        """Get user's survey sessions."""
        return SurveySession.objects.filter(user=self.request.user).order_by('-started_at')
    
    def retrieve(self, request, pk=None):
        """Get session details."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Check if session is expired
        if session.is_expired() and session.status not in ['completed', 'cancelled']:
            session.status = 'expired'
            session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """Submit an answer for a question."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        serializer = SubmitAnswerSerializer(
            data={
                'session_id': session.id,
                'question_id': request.data.get('question_id'),
                'choice_ids': request.data.get('choice_ids', []),
                'text_answer': request.data.get('text_answer', '')
            },
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                validated_data = serializer.validated_data
                session = validated_data['session']
                session_question = validated_data['session_question']
                question = validated_data['question']
                
                # Create or update answer
                answer, created = Answer.objects.get_or_create(
                    session=session,
                    question=question,
                    defaults={
                        'text_answer': validated_data.get('text_answer', '')
                    }
                )
                
                if not created:
                    answer.text_answer = validated_data.get('text_answer', '')
                    answer.selected_choices.clear()
                
                # Add selected choices
                if validated_data.get('choice_ids'):
                    answer.selected_choices.set(validated_data['choice_ids'])
                
                # Calculate score
                points_earned = answer.calculate_score()
                answer.save()
                
                # Update session question
                session_question.is_answered = True
                session_question.points_earned = points_earned
                session_question.save()
                
                # Check if all questions are answered
                remaining_questions = session.sessionquestion_set.filter(is_answered=False).count()
                
                if remaining_questions == 0:
                    # Complete session
                    session.status = 'completed'
                    session.completed_at = timezone.now()
                    session.save()
                    
                    # Calculate final score
                    final_score = session.calculate_final_score()
                    
                    # Update user history
                    history = UserSurveyHistory.objects.get(user=request.user, survey=session.survey)
                    history.current_status = 'completed'
                    
                    if not history.best_score or session.score > history.best_score:
                        history.best_score = session.score
                        history.best_percentage = session.percentage
                    
                    if session.is_passed:
                        history.is_passed = True
                    
                    history.save()
                    
                    return Response({
                        'message': _('Survey completed'),
                        'session': SurveySessionSerializer(session, context={'request': request}).data,
                        'final_score': final_score
                    })
                
                return Response({
                    'message': _('Answer submitted successfully'),
                    'session': SurveySessionSerializer(session, context={'request': request}).data
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel active session."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        if session.status not in ['started', 'in_progress']:
            return Response(
                {'error': _('Cannot cancel this session')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'cancelled'
        session.save()
        
        # Update user history
        try:
            history = UserSurveyHistory.objects.get(user=request.user, survey=session.survey)
            history.current_status = 'cancelled'
            history.save()
        except UserSurveyHistory.DoesNotExist:
            pass
        
        return Response({
            'message': _('Session cancelled successfully'),
            'session': SurveySessionSerializer(session, context={'request': request}).data
        })
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get session progress and answered questions."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        progress = session.get_current_progress()
        
        # Get all session questions with answers
        session_questions = session.sessionquestion_set.select_related('question').order_by('order')
        questions_data = []
        
        for sq in session_questions:
            question_data = {
                'order': sq.order,
                'question_id': sq.question.id,
                'is_answered': sq.is_answered,
                'points_earned': sq.points_earned,
                'max_points': sq.question.points
            }
            
            # Add answer if exists
            try:
                answer = session.answers.get(question=sq.question)
                question_data['answer'] = AnswerSerializer(answer).data
            except Answer.DoesNotExist:
                question_data['answer'] = None
            
            questions_data.append(question_data)
        
        return Response({
            'progress': progress,
            'questions': questions_data,
            'session': SurveySessionSerializer(session, context={'request': request}).data
        })


class CurrentSessionView(APIView):
    """Get user's current active session."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current active session if any."""
        active_session = SurveySession.objects.filter(
            user=request.user,
            status__in=['started', 'in_progress']
        ).select_related('survey').first()
        
        if active_session:
            # Check if expired
            if active_session.is_expired():
                active_session.status = 'expired'
                active_session.save()
                return Response({'session': None})
            
            serializer = SurveySessionSerializer(active_session, context={'request': request})
            return Response({'session': serializer.data})
        
        return Response({'session': None})
