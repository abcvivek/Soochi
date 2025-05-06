"""
Shared data models for ideas and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

class Idea(BaseModel):
    """Model representing an idea extracted from content."""
    
    title: str = Field(..., description="A catchy, descriptive title for the idea")
    type: str = Field(..., description="SaaS, Startup, Open-Source, or General-Project")
    problemStatement: str = Field(..., description="Briefly describe the issue or opportunity the idea addresses")
    solution: str = Field(..., description="Explain the proposed solution briefly in no more than 100 words")
    targetAudience: str = Field(..., description="Identify the primary beneficiaries")
    innovationScore: float = Field(..., description="Measure of idea's innovative potential on a scale of 0-10")
    potentialApplications: str = Field(..., description="Mention areas or scenarios where the idea could be used")
    prerequisites: str = Field(..., description="Note any technologies, datasets, or skills needed")
    additionalNotes: str = Field(..., description="Any supplementary information, trends, or context")
    url_hash: Optional[str] = None
    embedding: Optional[List[float]] = None

class Response(BaseModel):
    """Model representing a response from an AI model."""
    
    endReason: Optional[str] = None
    output: Optional[List[Idea]] = None
