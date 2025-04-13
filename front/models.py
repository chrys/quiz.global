from django.db import models
from django.core.validators import MinValueValidator

class Quiz(models.Model):
    """
    Represents a collection of questions forming a complete quiz.
    
    This model stores basic quiz information including when it was created
    and optional description for additional context.
    """
    quiz_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "quizzes"
        ordering = ['-created_at']  # Newest quizzes first

    def __str__(self):
        return f"{self.title} (ID: {self.quiz_id})"

class Question(models.Model):
    """
    Represents an individual question within a quiz.
    
    Each question belongs to exactly one quiz (many-to-one relationship)
    and can have multiple answer options (one-to-many relationship).
    """
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('TF', 'True/False'),
    ]

    question_id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=3,
        choices=QUESTION_TYPES,
        default='MCQ'
    )
    order_in_quiz = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    class Meta:
        ordering = ['order_in_quiz']
        unique_together = ['quiz', 'order_in_quiz']

    def __str__(self):
        return f"Question {self.order_in_quiz} in {self.quiz.title}"

class AnswerOption(models.Model):
    """
    Represents a possible answer choice for a question.
    
    Each answer option belongs to exactly one question (many-to-one relationship)
    and includes the answer text and whether it's correct.
    """
    option_id = models.AutoField(primary_key=True)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options'
    )
    option_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ['option_id']

    def __str__(self):
        return f"Option for {self.question}: {self.option_text[:30]}"
