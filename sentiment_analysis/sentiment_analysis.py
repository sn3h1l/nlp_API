from transformers import pipeline
import re


class sentiments():

    def __init__(self) -> None:
        self.model_path = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
        self.sentiment_task = pipeline("sentiment-analysis", model=self.model_path, tokenizer=self.model_path)
    
    def analyze_sentiment(self,text, level='whole'):
        whole_result = self.sentiment_task(text)
        whole_sentiment = whole_result[0]


        if level == 'whole':
            whole_results = []
            whole_results.append({
                    'text': text,
                    'average': {'sentiment': whole_sentiment['label'],
                                'confidence': round(whole_sentiment['score'],2)}
                }) 
            return whole_results
        
        elif level == 'paragraph':       
            whole_results = []
            whole_results.append({
                    'text': text,
                    'average': {'sentiment': whole_sentiment['label'],
                                'confidence': round(whole_sentiment['score'],2)}
                })
            paragraphs = text.split('\n')        
            if not paragraphs or len(paragraphs) == 1 :
                return {'whole_sentiment': whole_results}
            
            else:
            # Analyze paragraph-level sentiment
                paragraph_results = []
                for paragraph in paragraphs:
                    paragraph = paragraph.strip()
                    if paragraph:  # Ensure non-empty paragraphs
                        paragraph_result = self.sentiment_task(paragraph)
                        paragraph_sentiment = paragraph_result[0]
                        paragraph_results.append({
                            'text': paragraph,
                            'sentiment': paragraph_sentiment['label'],
                            'confidence': round(paragraph_sentiment['score'],2)
                        })
                
                # Return results with whole sentiment
                return {'sentiment': whole_results, 'sentiment_results': paragraph_results }
                    
        
        elif level == 'sentence':
            # Break text into sentences (simple sentence splitting using full stops)
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
            whole_results = []
            whole_results.append({
                    'text': text,
                    'average': {'sentiment': whole_sentiment['label'],
                                'confidence': round(whole_sentiment['score'],2)}
                }) 
            # Check if sentences exist
            if not sentences or len(sentences) == 1:
                return {'whole_sentiment': whole_results}
            
            
            sentence_results = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:  # Ensure non-empty sentences
                    sentence_result = self.sentiment_task(sentence)
                    sentence_sentiment = sentence_result[0] 
                    sentence_results.append({
                        'text': sentence,
                        'sentiment': sentence_sentiment['label'],
                        'confidence': round(sentence_sentiment['score'],2)
                    })
            
            # Return results with whole sentiment
            return {'sentiment': whole_results, 'sentiment_results': sentence_results}
        
        else:
            raise ValueError("Invalid level specified. Choose from 'whole', 'paragraph', or 'sentence'.")

text = "The product is great. However, the customer service needs improvement. Overall, I am satisfied with the purchase."
results = sentiments().analyze_sentiment(text, level='sentence')
print(type(results))