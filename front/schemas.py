from pydantic import BaseModel, Field, RootModel
from typing import List

class Option(BaseModel):
    option_id: str = Field(..., pattern="^(a|b|c|d)$", description="Option ID must be one of 'a', 'b', 'c', or 'd'")
    text: str = Field(..., description="Text of the option")

class QuizQuestion(BaseModel):
    id: str = Field(..., pattern="^q_[a-zA-Z]*_[0-9]{3}$", description="ID must match the pattern 'q_topic_XXX'")
    topic: str = Field(..., description="Topic of the question")
    difficulty: str = Field(..., pattern="^(Easy|Medium|Hard)$", description="Difficulty must be 'Easy', 'Medium', or 'Hard'")
    type: str = Field(..., pattern="^MCQ$", description="Type must be 'MCQ'")
    question_text: str = Field(..., description="The text of the question")
    options: List[Option] = Field(..., min_items=4, max_items=4, description="List of 4 options")
    correct_answer_id: str = Field(..., pattern="^(a|b|c|d)$", description="Correct answer ID must be one of 'a', 'b', 'c', or 'd'")
    explanation: str = Field(..., description="Explanation of the correct answer")

class QuizSchema(RootModel[List[QuizQuestion]]):
    """Root model for a list of quiz questions."""