import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline

# --- 1. Training Data (Your Labeled Examples) ---
# The model learns to classify phrases based on the intent label provided here.
data = {
    'text': [
        # GREETING (15 Examples)
        "hi there", "hello", "good morning", "hey", "how are you doing", "what's up",
        "good day", "hey chatbot", "greetings", "hello RenTera", "what can you do",
        "can you help me", "I need some information", "start conversation", "hi",

        # GOODBYE (15 Examples)
        "bye now", "thanks, goodbye", "I'm done", "see you later", "all set, bye",
        "that's all for now", "gonna go", "signing off", "have a good day", "i need to leave",
        "talk to you soon", "end chat", "cheers bye", "bye", "finished",

        # THANKS (15 Examples)
        "thank you", "thanks a lot", "that was helpful", "much appreciated", "cheers",
        "got it, thanks", "you're great, thanks", "you were very helpful", "thank you for the information",
        "I appreciate the help", "thanks", "perfect, thanks", "very helpful", "thanks for clarifying",
        "good bot thanks",

        # GENERAL_HELP (15 Examples)
        "how do i use this website", "I don't know where to start", "what are your main functions",
        "I'm confused about the process", "where can I find help", "can you guide me through the site",
        "need some general help", "what kind of questions can i ask", "I need assistance",
        "help with your platform", "what are the categories", "show me the list of options",
        "how to navigate the website", "need to understand the rental process", "where is the FAQ",

        # PRICING_PROPRIETOR (15 Examples)
        "What is the charge for listing an apartment on RenTera?", "How much do proprietors pay to upload?",
        "cost per room for listing", "Explain the listing fee structure for owners.",
        "How long does the 100 rupee fee last?", "duration of the proprietor listing",
        "price to post a house", "Are there annual fees for owners?", "listing fees for offices",
        "How much for a shutter listing?", "is the listing fixed for 3 months",
        "cost to advertise my property", "what does it cost to feature a home", "charges for landlords",
        "is the room price 100",

        # PRICING_RENTER (15 Examples)
        "Is there a commission for renters?", "Do I pay RenTera to rent a house?",
        "is the service free for tenants", "What is the cost for renters?",
        "are there any charges for using the search filter", "fees for finding a rental",
        "do i have to pay for the application", "is the rental search free",
        "cost to contact a landlord", "Charges for rentors", "how much for apartment viewing",
        "does the tenant pay anything to RenTera", "what are the rentor fees",
        "Is browsing properties free?", "zero charges for renting a place",

        # FEATURES_PLATFORM (15 Examples - Focus on Specific Tools)
        "Can I chat directly with the owner?", "is there an in-app messaging feature",
        "how does the filtering work during search", "Can I see a map of the property location?",
        "Is parking information available in the details?", "tell me about property basics like water supply",
        "How to filter for apartments with internet", "what can I see in property details",
        "Do you support direct messaging?", "What type of buildings can I list?",
        "how to find offices on the platform", "Can I filter based on the number of rooms?",
        "Do the details show utilities?", "where is the exact location map", "how to save a favorite property",

        # ACCOUNT_ACCESS (15 Examples - Focus on Login/Signup HOW-TO)
        "How do I sign up for an account?", "what are the steps for registration",
        "where is the login page", "how to unlock all features",
        "Is login mandatory to view properties?", "step-by-step guide to log in",
        "I can't see the owner's phone number, why?", "trouble logging into my account",
        "need to register to send a request", "forgot my password",
        "how to create a new profile", "how to set up my proprietor account",
        "can i browse without logging in", "where is the 'Register' button",
        "is there a tutorial for signing up",

        # SAFETY_VERIFICATION (15 Examples)
        "What documents are needed for verification?", "Do you check proprietor land numbers?",
        "why do I need to provide citizenship documents", "How is the safety of the platform ensured?",
        "Is there a background check for owners?", "what paperwork is needed to list a property",
        "renter citizenship requirement", "Are all listings verified?",
        "what security checks do you perform", "is my identity safe with you",
        "what document verification is required for tenants", "owner verification process",
        "Do I need to submit my ID?", "what does RenTera do for safety",
        "security measures",

        # REPORT_ISSUE (15 Examples)
        "The chat feature is broken", "I found an inappropriate listing",
        "I have a technical bug", "The map is not loading correctly",
        "How do I report a fake listing?", "I need to talk to human support",
        "The filtering feature is crashing", "I can't upload my property photos",
        "There is an error on the page", "I need to file a complaint",
        "who do I contact for site issues", "report bad behavior",
        "site is not working", "need to report a listing", "bug in the system",

        # ONBOARDING_PROCESS (15 Examples - Focus on User Journey/Next Steps)
        "what is the next step after searching", "how do I request a viewing of an apartment",
        "what is the process to rent a property", "how do I contact the proprietor about a place",
        "I found a listing, now what should I do", "what are the steps for renters",
        "How do I finalize a rental agreement", "how to show interest in a house",
        "what to do after finding a property", "what is the procedure for renting",
        "how do I get the keys", "what happens after I click 'Send Request'",
        "how to follow up on a property", "what's the best way to secure a place",
        "where do I begin looking for a house",
    ],
    'intent': [
        'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting', 'greeting',
        'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye', 'goodbye',
        'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks', 'thanks',
        'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help', 'general_help',
        'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor', 'pricing_proprietor',
        'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter', 'pricing_renter',
        'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform', 'features_platform',
        'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access', 'account_access',
        'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification', 'safety_verification',
        'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue', 'report_issue',
        'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process', 'onboarding_process',
    ]
}

#text: During Training: The model reads these sentences and uses the TfidfVectorizer (the first NLP step) to convert them into numbers. It learns what words tend to appear together for a specific topic (e.g., "cost," "price," and "fee" are all related).

# During Prediction: When a user types a new sentence (one the AI has never seen), the model converts it to numbers and compares its numerical fingerprint against the numerical fingerprints it learned from this data list.
# intent:During Training: The model is explicitly told: "If you see a sentence containing 'price' or 'cost,' you must classify it as the category pricing." The SVC algorithm (the classifier) draws its mathematical boundary based on this target label.
# During Prediction: After the model predicts that the new user sentence belongs to the category pricing, the Django view uses that exact label ("pricing") as the key to look up the final, pre-written answer in the STATIC_RESPONSES dictionary.
df = pd.DataFrame(data)
#It converts the dictionary into a two-column table (DataFrame). This structure makes it easy for the training function to associate each sentence with its correct label.

# --- 2. Model Pipeline ---
pipeline = Pipeline([
    ('vectorizer', TfidfVectorizer(ngram_range=(1, 2), stop_words='english')),
    ('classifier', SVC(kernel='linear', C=1)) 
])
#When we talk about the SVC Classifier, its entire job during training is to create a perfect map, linking the sentence's numerical features to the intent label.

# --- 3. Training the Model ---
print("--- Starting model training ---")
pipeline.fit(df['text'], df['intent'])
print("--- Training complete. ---")

# --- 4. Saving the Model ---
app_dir = os.path.dirname(__file__)
model_path = os.path.join(app_dir, 'intent_model.joblib')
joblib.dump(pipeline, model_path) #The joblib.dump() function is the critical step that transforms the "brain" (the trained SVC equations and TF-IDF vocabulary) into a permanent file.
print(f"Model saved successfully to: {model_path}")

#vectorizer
# In Python, TfidfVectorizer is a class. When you write TfidfVectorizer(...), you are creating an object (an instance of that class) which has methods (functions) like fit and transform.Its main goal is to assign a single numerical importance score to every unique word in your entire set of training sentences. This score is calculated using two factors: term Frequency (TF): How often the word appears in the current sentence. (If "price" appears 3 times in a sentence, TF is high for that sentence).Inverse Document Frequency (IDF): How rare the word is across all sentences. (If "the" appears in every sentence, IDF is low. If "leasing" only appears in one sentence, IDF is high).By multiplying TF and IDF, the model gets a score where words like "pricing" or "support" have high importance, and words like "is" or "a" have low importance.
# By setting ngram_range=(1, 2), you are telling the Vectorizer to consider both single words and two-word phrases.

# Why it's necessary: If the model only looked at 1-grams, it would see the word "customer" and the word "service" as two separate, weak signals. By including the 2-gram "customer service," the model sees a single, strong signal that points directly to the "contact" intent. This significantly improves accuracy and understanding of compound terms.
#The AI learns: "Ignore the weak signals from 'customer' and 'service.' If I see the 'customer service' feature, I am 99% confident the intent is Contact."
#classifier

# he joblib file does not contain a function; it contains the entire trained data needed for the function to run. It holds the two key components of your pipeline:

# A. The TfidfVectorizer Data (The Interpreter)
# This component ensures that when a new user types a sentence, it is converted into the exact same numerical fingerprint used during training. The file stores:

# Vocabulary List: The definitive list of every single Word Feature the model recognizes ("fee", "cost", "support", etc.).

# IDF Scores: The fixed, global rarity score for every single Word Feature (used to calculate the new sentence's TF-IDF scores).

# B. The SVC Data (The Separating Lines)
# This component stores the final output of the learning process:

# The W-Weights: The single, fixed set of optimized W-weights for each SVC equation (e.g., W 
# fee
# ​
#   for the SVC 
# pricing
# ​
#   equation, W 
# fee
# ​
#   for the SVC 
# contact
# ​
#   equation, etc.).

# The Label List: A list of all the Intent Labels the model can predict ("pricing", "contact", etc.).

# In summary, the file contains all the numbers—the W-weights and IDF scores—that define the rules of the AI.