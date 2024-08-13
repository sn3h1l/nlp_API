import torch
from torch.utils.data import DataLoader, TensorDataset
from transformers import MBart50TokenizerFast, MBartForSequenceClassification 
import warnings 
warnings.filterwarnings('ignore')

class toxic_classifier():
    def __init__(self):
        self.device = torch.device( 
            'cuda') if torch.cuda.is_available() else torch.device('cpu')

        self.get_lang_code = {
            "hi":"hi_IN",
            "en":"en_XX"
        }
        self.model_name = "kumarsushant36/multiLingual_Toxic_Text_Classification"
        self.Bart_Tokenizer = MBart50TokenizerFast.from_pretrained(self.model_name) 
        self.Bart_Model = MBartForSequenceClassification.from_pretrained( 
        self.model_name).to(self.device)

    def predict_user_input(self,input_text, lang,): 
        if lang not in self.get_lang_code:
            return None
        

        user_input = [input_text] 

        self.Bart_Tokenizer.src_lang = self.get_lang_code[lang]
        user_encodings = self.Bart_Tokenizer( 
            user_input, truncation=True, padding=True, return_tensors="pt") 

        user_dataset = TensorDataset( 
            user_encodings['input_ids'], user_encodings['attention_mask']) 

        user_loader = DataLoader(user_dataset, batch_size=1, shuffle=False) 

        self.Bart_Model.eval() 
        with torch.no_grad(): 
            for batch in user_loader: 
                input_ids, attention_mask = [t.to(self.device) for t in batch] 
                outputs = self.Bart_Model(input_ids, attention_mask=attention_mask) 
                logits = outputs.logits 
                predictions = torch.sigmoid(logits) 

        predicted_labels = (predictions.cpu().numpy() > 0.5).astype(int) 
        labels_list = ['toxic', 'severe_toxic', 'obscene', 
                    'threat', 'insult', 'identity_hate']  
        result = [label for label, pred in zip(labels_list, predicted_labels[0]) if pred == 1]
        print(predicted_labels)
        return result


# text = "I will kill you"
# src_lang = "en"
# result = toxic_classifier().predict_user_input(input_text=text, lang=src_lang)
# print(result)
