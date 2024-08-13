from fastapi import FastAPI, Query
from pydantic import BaseModel
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ner.entities import Detector 
from typing import List, Optional, Dict, Any
from sentiment_analysis.sentiment_analysis import sentiments
from cont_mod.moderation import Text_Moderator
from summarization.summary_groq import Summarize
from pii.redaction import PII_Redactor
from translation.translation import Translate
from toxic_classification.toxic import toxic_classifier 

app = FastAPI()


class TranslationRequest(BaseModel):
    target_language: str
    translation_domain: str

class PiiRedactionRequest(BaseModel):
    redact_pii_sub: str
    redact_pii_types: List[str]

class SummaryRequest(BaseModel):
    summary_model: str
    summary_type: str

class EntityRecognitionRequest(BaseModel):
    entity_types: List[str]

class SentimentRequest(BaseModel):
    level: str

class ContentModerationRequest(BaseModel):
    moderation_types: List[Any]

class text_analysis_request(BaseModel):
    text: str
    language: str
    translation: Optional[TranslationRequest]
    pii_redaction: Optional[PiiRedactionRequest]
    summary: Optional[SummaryRequest]
    entity_recognition: Optional[EntityRecognitionRequest]
    sentiment: Optional[SentimentRequest]
    content_moderation: Optional[ContentModerationRequest]

class TranslationResponse(BaseModel):
    translated_text: str

class SummaryResponse(BaseModel):
    summarised_text: str

class EntityRecognitionResponse(BaseModel):
    entities: Dict[str,Any]

class SentimentResponse(BaseModel):
    sentiments: Dict[str,Any]

class PiiRedactionResponse(BaseModel):
    redacted_text: str
    redaction_results: List[Any]

class ModerationResult(BaseModel):
    moderated_text : str

class ContentModerationResponse(BaseModel):
    moderated_text: str
    moderation_results: List[ModerationResult]

class text_analysis_response(BaseModel):
    translation: Optional[TranslationResponse] = None
    summary: Optional[SummaryResponse]=None
    entity_recognition: Optional[EntityRecognitionResponse] = None
    sentiment: Optional[SentimentResponse]=None
    pii_redaction: Optional[PiiRedactionResponse] = None
    content_moderation: Optional[ContentModerationResponse] = None

class api_response(BaseModel):
    results: text_analysis_response

@app.post("/api/v2/text-analyse", response_model=api_response)
async def text_analyse(
    request: text_analysis_request,
    translate: bool = Query(False),
    summary: bool = Query(False),
    sentiment: bool = Query(False),
    detect_entities: bool = Query(False),
    content_safety: bool = Query(False),
    pii_redaction: bool = Query(False)
):
    results = {}
    
    if translate and request.translation:
        try:
            translator = Translate()
            Translated_text = translator.translate(target_lang=request.translation.target_language, source_lang=request.language, text=request.text)
        except:
            Translated_text=""
        results['translation'] = TranslationResponse(
            translated_text=Translated_text
        )
    
    if summary and request.summary:
        try:
            summarizer = Summarize()
            summarized_text = summarizer.summary(text=request.language,source_lang=request.language,summary_type=request.summary.summary_type)
        except:
            summarized_text=""
        results['summary'] = SummaryResponse(summarised_text=summarized_text)

    if detect_entities and request.entity_recognition:
        try:
            extractor=Detector(request.text,request.language)
            ner_res=extractor.detect()
        except:
            ner_res={}

        results['entity_recognition'] = EntityRecognitionResponse(entities=ner_res)

    if sentiment and request.sentiment:
        try:
            sentiment_analyzer=sentiments()
            sentiment_results=sentiment_analyzer.analyze_sentiment(request.text,level=request.sentiment.level)
        except:
            sentiment_results={}

        results['sentiment'] = SentimentResponse(
            sentiments=sentiment_results
        )
    
    if pii_redaction and request.pii_redaction:
        try:
            redactor_object = PII_Redactor()
            Redacted_Text, Redaction_List = redactor_object.hide_details(text=request.text,redact_pii_types=request.pii_redaction.redact_pii_types)
        except:
            Redacted_Text=""
            Redaction_List=[]

        results['pii_redaction'] = PiiRedactionResponse(
            redacted_text=Redacted_Text,
            redaction_results=Redaction_List
        )

    if content_safety and request.content_moderation:
        try:
            moderator = Text_Moderator()
            Moderated_text, Moderation_result = moderator.moderate_text(
            lang_input=request.language,
            text=request.text
            )
        except:
            Moderated_text=""
            Moderation_result=[]

        results['content_moderation'] = ContentModerationResponse(
            moderated_text=Moderated_text,
            moderation_results=Moderation_result
        )

    return api_response(results=text_analysis_response(**results))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)