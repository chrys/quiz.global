from django.contrib import admin
from .models import Quiz, Question, AnswerOption

class AnswerOptionInline(admin.TabularInline):
    """Inline view for answer options"""
    model = AnswerOption
    extra = 4  # Show 4 empty option forms by default
    min_num = 4  # Require minimum 4 options
    max_num = 4  # Allow maximum 4 options

class QuestionInline(admin.StackedInline):
    """Inline view for questions"""
    model = Question
    extra = 1
    show_change_link = True

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin view for Quiz model"""
    list_display = ('quiz_id', 'title', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
    inlines = [QuestionInline]
    date_hierarchy = 'created_at'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin view for Question model"""
    list_display = ('question_id', 'quiz', 'question_type', 'order_in_quiz')
    list_filter = ('question_type', 'quiz')
    search_fields = ('question_text',)
    inlines = [AnswerOptionInline]

@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    """Admin view for AnswerOption model"""
    list_display = ('option_id', 'question', 'option_text', 'is_correct')
    list_filter = ('is_correct', 'question__quiz')
    search_fields = ('option_text',)
