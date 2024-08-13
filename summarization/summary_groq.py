import os
print(os.getcwd())

from groq import Groq
class Summarize():
    def __init__(self) -> None:
        #Future Fix : Change the key or check for usage expiration
        self.client = Groq(
                api_key="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")       
        self.Indian_languages = {
        "hi": "Hindi",
        "en": "English",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "ml": "Malayalam",
        "kn": "Kannada",
        "gu": "Gujarati",
        "mr": "Marathi",
        "or": "Odia",
        "pa": "Punjabi",
        "as": "Assamese",
        }
    def summary(self,text, summary_type, source_lang, target_lang='en' ):
    # print(Indian_languages[target_lang])
        if source_lang in self.Indian_languages:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                    'role': 'system',
                    'content': f"""Your goal is to summarize the text in english given to you in a {summary_type} type of summary. """
                    },
                    {
                        "role": "user",
                        "content": f"{text}",
                    }
                ],
                model="llama3-8b-8192",
            )

            return chat_completion.choices[0].message.content
        else: return None


# text = """
# प्रस्तावना

# गाय एक पालतु पशु है। प्राचीन काल से ही गौ माता को देवी समान समझा जाता है। हर मंगल कार्य में गाय के ही चीजों का प्रयोग होता है। यहां तक की गाय के उत्सर्जी पदार्थ (गोबर, मूत्र) का भी इस्तेमाल होता है। जिसे पंचगव्य(दूध, दही, घी, गोबर, मूत्र) की उपमा दी गयी है। इन तत्वों का औषधिय महत्व भी है। बहुत सारी दवाईयों के निर्माण में घी और गोमूत्र का इस्तेमाल किया जाता है।

# गाय की शारीरिक संरचना

# गाय की शारीरिक संरचना में गाय के दो सींग, चार पैर, दो आंखे, दो कान, दो नथुने, चार थन, एक मुंह और एक बड़ी सी पूँछ होती है। गाय के खुर उन्हें चलने में मदद करते हैं। उनके खुर जुते का काम करते है तथा चोट और झटकों आदि से बचाते है। गाय की प्रजातियां पूरे विश्व भर में पाईं जाती है। कुछ प्रजातियों में सींग बाहर दिखाई नहीं देते। दुग्ध उत्पादन में भारत का समुचे विश्व में पहला स्थान है। गाय का दूध बेहद लाभदायक और पौष्टिक होता है।

# गाय के महत्व

# भारत में गाय का पौराणिक, आर्थिक और धार्मिक दृष्टि से बहुत महत्त्व है। पुराणों के अनुसार गाय की हत्या वर्जित है, यह जघन्य पाप है। भगवान शिव की सवारी नंदी गाय है।  धार्मिक और सामाजिक तौर पर गाय को माता का दर्जा प्राप्त है। गाय आर्थिक दृष्टि से भी महत्वपूर्ण है। गाय से हमें घी, दूध, गोबर आदि प्राप्त होते है।

# निष्कर्ष

# भारत में गाय को माता का दर्जा दिया गया है। और भी बहुत पालतु जानवर है, लेकिन उन सबमें गाय का सर्वोच्च स्थान है। हम सभी को गाय के पौराणिक और सामाजिक महत्त्व को समझना चाहिए। हम सभी को गाय का सम्मान करना चाहिए।
# """
# print(Summarize().summary(text, 'bullets', 'hi'))
