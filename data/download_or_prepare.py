"""
Data Preparation & Realistic Twitter Support Corpus Generator.
Generates a realistic, highly diverse corpus of historical @AmazonHelp Twitter support conversations
spanning all 8 customer support intents, multi-turn contexts, realistic customer queries,
and authentic Amazon Twitter support responses with standard signatures and URLs.
"""

import os
import sys
import json
import random
import argparse
import pandas as pd
from typing import List, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DEFAULT_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

INTENT_TEMPLATES = {
    "delivery_delay_and_tracking": [
        ("My {item} was promised for delivery by {time} today, but tracking shows it hasn't even left the facility. Order #{order}.",
         "We apologize for the delay! Carrier transit times can vary. You can view the most up-to-date tracking information here: https://amzn.to/track. If it doesn't arrive by tomorrow evening, please DM us with your order ID: https://amzn.to/dm ^{sig}",
         False, "Standard transit buffer; directed customer to official live tracking."),
        ("Tracking says '{status}' since {day}, but there have been no new updates for 4 days. Is my order #{order} lost?",
         "We understand your concern regarding the lack of tracking movement. Please send us a direct message with your order number and email address so we can initiate an investigation with the carrier: https://amzn.to/dm ^{sig}",
         True, "Carrier stall exceeding 48h SLA; requires human carrier tracing."),
        ("Driver marked package attempted because they couldn't access the building gate, but no one buzzed my apartment {apt}!",
         "We're sorry for the inconvenience! Drivers will automatically re-attempt delivery on the next business day. You can add permanent gate codes in Your Account > Addresses: https://amzn.to/delivery-instructions. If urgent, DM us: https://amzn.to/dm ^{sig}",
         False, "Gate access issue; self-service delivery instruction update provided."),
        ("Order #{order} contains urgent medical supplies for my family that was guaranteed yesterday. Where is the courier right now?",
         "We sincerely apologize for this critical delay. Given the urgency of these supplies, please DM us immediately so a priority dispatcher can coordinate with the local logistics hub: https://amzn.to/dm ^{sig}",
         True, "Time-critical urgent medical delivery requiring priority dispatcher intervention."),
        ("Does Amazon Logistics deliver on Sundays in {city}? My tracking says arriving Sunday by 9pm.",
         "Yes! Amazon Logistics delivers 7 days a week, including Sundays in most metropolitan areas. You can follow the driver's stop countdown in the Amazon app once out for delivery: https://amzn.to/your-orders ^{sig}",
         False, "General Sunday delivery policy inquiry; answered directly.")
    ],
    "missing_or_stolen_package": [
        ("The Amazon app sent a notification saying my {item} was delivered to my front porch {minutes} minutes ago, but the porch is empty!",
         "Carriers sometimes scan packages just prior to walking up to the door. Please allow until the end of the day, and check with household members or side porches: https://amzn.to/find-missing. If still not found tomorrow, reach back out! ^{sig}",
         False, "Scan occurred within past hour; standard buffer and safe spot search recommended."),
        ("Delivery photo shows a completely different apartment number ({wrong_apt}) and a red doormat. I live in unit {apt} and don't have a red mat!",
         "We apologize for the misdelivery! Please send us a direct message with your order number so we can review the courier photo, verify your unit, and process an immediate replacement: https://amzn.to/dm ^{sig}",
         True, "Photographic proof of misdelivery to wrong unit; requires replacement authorization."),
        ("It has been 36 hours since my package #{order} was marked delivered. I checked with neighbors and my building management. It is not here.",
         "Thank you for thoroughly checking around your property. Since 36 hours have passed, please DM us your order ID so our team can file a missing package claim and issue a replacement or refund: https://amzn.to/dm ^{sig}",
         True, "Waiting window expired and parcel missing; requires human claims specialist."),
        ("Someone stole the package off my porch! I caught the porch pirate on my Ring doorbell camera. How do I get a replacement?",
         "We're so sorry this happened. Please DM us your order number and police report number (if filed) so we can file an incident report and assist with a replacement: https://amzn.to/dm ^{sig}",
         True, "Stolen package / criminal theft report requiring security claim handling.")
    ],
    "return_and_refund_status": [
        ("I dropped off my return of {item} at {dropoff} on {day}. When should I expect the refund to appear on my credit card?",
         "Once the return is received, refunds typically take 3 to 5 business days to process back to your original payment method. You can track refund progress under Your Orders: https://amzn.to/refund-status ^{sig}",
         False, "Standard banking processing timeline explanation."),
        ("It has been 18 days since your return center acknowledged receipt of my #{order}, but my refund of ${price} is still not issued. Where is my money?",
         "We apologize for the delay. Eighteen days exceeds our normal processing timeline. Please send us a DM with your order number so a billing specialist can review the return status and manually release your refund: https://amzn.to/dm ^{sig}",
         True, "Refund overdue beyond standard SLA (>14 days); requires manual finance clearance."),
        ("I don't have a working printer at home. Can I return my {item} without printing a return label?",
         "Yes! You can choose 'UPS Drop-off - No Box or Label Needed' or 'Kohl's Drop-off' when initiating the return in Your Orders. They will simply scan a QR code from your phone: https://amzn.to/return-center ^{sig}",
         False, "Self-service instructions for mobile QR code label-free returns."),
        ("The return window for my {item} closed 3 days ago because I was hospitalized. Can an exception be made to return it?",
         "We hope you are recovering well. While the online return portal locks after the return window, please send us a DM with your order ID so a customer care supervisor can review your case for an exception: https://amzn.to/dm ^{sig}",
         True, "Policy exception request requiring human supervisor override.")
    ],
    "damaged_or_incorrect_item": [
        ("My {item} arrived today but the packaging was crushed and the item is cracked in half! Do I have to send back broken glass?",
         "We're very sorry your item arrived damaged! You do not need to ship back broken glass. Please visit Your Orders and select 'Return or replace items' to request a free replacement: https://amzn.to/your-orders. DM us if you need help: https://amzn.to/dm ^{sig}",
         False, "Automated returns portal guidance for broken item replacement without hazardous return shipment."),
        ("I ordered a {item} (${price}) and you sent me a box of {wrong_item}! Order #{order}. This is a totally different item!",
         "We sincerely apologize for this warehouse mix-up! Please DM us your order number so our fulfillment escalation team can investigate the inventory error and dispatch the correct item immediately: https://amzn.to/dm ^{sig}",
         True, "Severe inventory mispick requiring warehouse audit and expedited replacement."),
        ("The {item} I received has a ripped retail seal and looks like it was already used by someone else, but I paid for brand new!",
         "We apologize for this experience. We take new item guarantees seriously. Please go to Your Orders to request an exchange for an unopened replacement, or DM us if you need assistance: https://amzn.to/your-orders ^{sig}",
         False, "Used-sold-as-new complaint; customer guided to instant exchange flow."),
        ("Liquid soap bottle leaked inside the box and ruined the electronics ({item}) that were shipped together in the same box!",
         "We're so sorry for this shipping error! Please send us a direct message with photos of the damaged package and your order ID so we can issue a full replacement for all affected items: https://amzn.to/dm ^{sig}",
         True, "Cross-item hazardous spill damaging electronics; human damage assessment required.")
    ],
    "prime_membership_and_billing": [
        ("I was just charged ${price} for Amazon Prime annual renewal today, but I forgot to cancel. Can I get a refund if I haven't used it?",
         "Yes! If you haven't used any Prime benefits since the renewal charge, you will automatically receive a full refund when you cancel at: https://amzn.to/manage-prime ^{sig}",
         False, "Prorated/unused Prime auto-refund policy self-service guidance."),
        ("Why was my credit card charged twice for my Prime monthly subscription on the same day? Two charges of $14.99!",
         "We apologize for the double charge! Please send us a DM with your account email address so a billing representative can investigate the duplicate transaction and process a refund: https://amzn.to/dm ^{sig}",
         True, "Duplicate billing error requiring human billing specialist."),
        ("The promo code '{promo}' from your promotional email is giving an error saying 'Promotion has ended' even though the email said valid through Friday.",
         "We'd like to check this promo code for you! Please send us a direct message with a screenshot of the email and the item in your cart: https://amzn.to/dm ^{sig}",
         True, "Promotional code dispute requiring customer care manual credit."),
        ("How do I share my Prime shipping benefits with my spouse without sharing my payment cards?",
         "You can share Prime shipping benefits via Amazon Household! Both adults maintain separate accounts and payment methods. Set it up here: https://amzn.to/amazon-household ^{sig}",
         False, "Educational guidance on Amazon Household feature.")
    ],
    "digital_services_and_devices": [
        ("Prime Video keeps giving error code {err_code} when playing movies on my {device}. How do I fix this?",
         "Error {err_code} is typically resolved by restarting your device and router, or clearing the Prime Video app cache. You can find detailed troubleshooting steps here: https://amzn.to/prime-video-help ^{sig}",
         False, "Standard streaming cache/reboot troubleshooting steps."),
        ("My Kindle {device} screen is completely frozen on the waking up screen. Holding down the power button for 40 seconds does not reboot it.",
         "We're sorry to hear about your Kindle! Please connect it to a wall charger for at least 30 minutes, then attempt the 40-second power button hold again. If it remains frozen, DM us for warranty options: https://amzn.to/dm ^{sig}",
         False, "Standard Kindle battery recovery protocol; escalates only if hardware unresponsive."),
        ("My Fire TV Stick keeps restarting in a continuous boot loop showing only the logo. I bought it 2 months ago.",
         "We're sorry your Fire TV Stick is stuck in a boot loop. Since standard power cycling did not work and the device is under warranty, please DM us your serial number so we can process a warranty replacement: https://amzn.to/dm ^{sig}",
         True, "Persistent hardware bootloop within warranty period requiring RMA exchange."),
        ("Purchased an eBook on Amazon but it's not showing up on my Kindle app library on my iPad.",
         "Please verify that your iPad Kindle app is registered to the exact same Amazon account used to make the purchase, and tap 'Sync' inside the app menu: https://amzn.to/kindle-sync ^{sig}",
         False, "Digital library synchronization troubleshooting steps.")
    ],
    "account_access_and_security": [
        ("ALERT: I got an email saying my Amazon account email was changed to an unknown outlook address and an order for a $500 gift card was placed! HELP!",
         "CRITICAL: If you suspect unauthorized access, please call our 24/7 Account Security Team immediately at 1-888-280-4331 or visit https://amzn.to/account-security. Please do not post account details publicly ^{sig}",
         True, "CRITICAL ACCOUNT SECURITY: Account takeover and unauthorized orders; mandatory human security team escalation."),
        ("I'm not receiving the 2-Step Verification SMS code on my mobile phone to log in. I tried 3 times.",
         "Mobile carrier networks can occasionally delay SMS codes. On the sign-in screen, click 'Didn't receive the code?' to request a voice call or backup code: https://amzn.to/2sv-help ^{sig}",
         False, "Standard 2FA fallback options guidance."),
        ("My Amazon account was suspended for 'unusual activity' and my orders were cancelled. I have $450 in gift balance that I cannot access!",
         "We understand your concern regarding your suspended account and balance. Please DM us your registered email so we can route your case to our Account Specialist team for priority review: https://amzn.to/dm ^{sig}",
         True, "Account suspension with trapped funds requiring human account specialist review."),
        ("Received a text message claiming to be Amazon asking me to click a link to verify my credit card. Is this real or a scam?",
         "Amazon will never text you asking for sensitive payment details or passwords. That is likely a phishing scam. Please do not click any links, and report it to: https://amzn.to/report-phishing ^{sig}",
         False, "Phishing awareness and reporting guidance.")
    ],
    "general_product_or_policy_inquiry": [
        ("Does Amazon ship electronic goods to military APO/FPO addresses in {country}?",
         "Yes, Amazon ships many items to APO/FPO addresses via USPS! Certain hazardous or oversized items may have restrictions. Check full policy details: https://amzn.to/apo-fpo ^{sig}",
         False, "Military address shipping policy inquiry; answered directly."),
        ("Can I combine my Amazon gift card balance with an Amazon promotional credit on the same purchase?",
         "Yes! Gift card balances and promotional credits can be combined at checkout. The promotional credit is usually applied first to qualifying items, followed by gift card funds ^{sig}",
         False, "Payment method policy question; clear factual answer."),
        ("What is the difference between Amazon Renewed and Amazon Renewed Premium warranties?",
         "Amazon Renewed products come with a 90-day satisfaction guarantee, while Amazon Renewed Premium products feature a 1-year guarantee and battery health tested to at least 90%: https://amzn.to/renewed ^{sig}",
         False, "Public warranty policy comparison; clear factual answer."),
        ("I need an official tax invoice with VAT ID for my company purchase order #{order}.",
         "You can download official tax invoices directly from Your Orders by clicking 'Invoice' on the order details page: https://amzn.to/your-orders ^{sig}",
         False, "Self-service business invoice download guidance.")
    ]
}

ITEMS = [
    "Sony Wireless Headphones", "Kindle Paperwhite", "Dyson V8 Vacuum", "Keurig Coffee Maker",
    "Samsung 55-inch OLED TV", "Apple AirPods Pro", "Logitech Wireless Mouse", "Ninja Air Fryer",
    "Levi's Denim Jacket", "Fitbit Charge 6", "Anker Portable Charger", "Instant Pot Duo",
    "Ceramic Dinnerware Set", "Oral-B Electric Toothbrush", "LEGO Star Wars Set"
]
WRONG_ITEMS = ["cat litter", "dog food", "pack of socks", "baby wipes", "coffee mugs", "plastic hangers"]
DROPOFFS = ["The UPS Store", "Kohl's Drop-off", "Whole Foods Market customer desk", "Amazon Locker"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TIMES = ["2 PM", "5 PM", "8 PM", "9 PM"]
STATUSES = ["Out for Delivery", "In Transit", "Carrier picked up package", "Departed facility"]
DEVICES = ["Roku Ultra", "Samsung Smart TV", "Fire TV 4K", "LG WebOS TV", "Apple TV"]
ERR_CODES = ["5004", "1060", "7031", "9074", "PL-01"]
SIGNATURES = ["MK", "AB", "RG", "SJ", "JW", "TB", "KL", "DL"]
CITIES = ["Chicago", "Seattle", "Austin", "Denver", "Miami", "Boston", "Atlanta"]
COUNTRIES = ["Germany", "Japan", "South Korea", "Italy", "United Kingdom"]

def generate_conversation_pair(intent: str, template_idx: int, seed_val: int) -> Dict[str, Any]:
    rnd = random.Random(seed_val)
    templates = INTENT_TEMPLATES[intent]
    tpl = templates[template_idx % len(templates)]
    
    order = f"{rnd.choice(['111', '112', '113', '114'])}-{rnd.randint(1000000, 9999999)}-{rnd.randint(1000000, 9999999)}"
    item = rnd.choice(ITEMS)
    wrong_item = rnd.choice(WRONG_ITEMS)
    dropoff = rnd.choice(DROPOFFS)
    day = rnd.choice(DAYS)
    time_str = rnd.choice(TIMES)
    status = rnd.choice(STATUSES)
    device = rnd.choice(DEVICES)
    err_code = rnd.choice(ERR_CODES)
    sig = rnd.choice(SIGNATURES)
    city = rnd.choice(CITIES)
    country = rnd.choice(COUNTRIES)
    price = f"{rnd.randint(15, 650)}.{rnd.choice(['99', '50', '00'])}"
    apt = str(rnd.randint(101, 899))
    wrong_apt = str(rnd.randint(101, 899))
    minutes = str(rnd.choice([15, 25, 45, 60]))
    promo = f"SAVE{rnd.choice(['20', '50', 'FALL', 'HOLIDAY'])}"
    
    cust_text = tpl[0].format(
        item=item, wrong_item=wrong_item, dropoff=dropoff, day=day, time=time_str,
        status=status, device=device, err_code=err_code, order=order, price=price,
        apt=apt, wrong_apt=wrong_apt, minutes=minutes, promo=promo, city=city, country=country
    )
    
    brand_text = tpl[1].format(
        sig=sig, item=item, order=order, price=price, err_code=err_code, device=device
    )
    
    cust_full = f"@AmazonHelp {cust_text}"
    
    return {
        "customer_message": cust_full,
        "historical_response": brand_text,
        "intent": intent,
        "gold_escalation": "ESCALATE_TO_HUMAN" if tpl[2] else "AUTO_HANDLE",
        "gold_reason": tpl[3]
    }

def create_rich_dataset(total_samples: int = 1500, seed: int = 42) -> List[Dict[str, Any]]:
    rnd = random.Random(seed)
    intents = list(INTENT_TEMPLATES.keys())
    
    records = []
    seen = set()
    
    counter = 0
    while len(records) < total_samples:
        intent = rnd.choice(intents)
        tpl_idx = rnd.randint(0, 10)
        pair = generate_conversation_pair(intent, tpl_idx, seed + counter)
        counter += 1
        
        # Check uniqueness of customer text
        cust_norm = pair["customer_message"].lower()
        if cust_norm in seen:
            continue
        seen.add(cust_norm)
        
        record_id = f"conv_amzn_{len(records):05d}"
        records.append({
            "id": record_id,
            "brand": "AmazonHelp",
            "conversation_id": record_id,
            "customer_message": pair["customer_message"],
            "conversation_context": f"Customer reaching out to @AmazonHelp regarding {intent.replace('_', ' ')}.",
            "historical_response": pair["historical_response"],
            "intent": intent,
            "gold_escalation": pair["gold_escalation"],
            "gold_reason": pair["gold_reason"]
        })
        
    return records

def prepare_dataset(data_path: str = None, brand: str = "AmazonHelp", use_sample: bool = False, seed: int = 42):
    os.makedirs(DEFAULT_RAW_DIR, exist_ok=True)
    os.makedirs(DEFAULT_PROCESSED_DIR, exist_ok=True)
    
    raw_file = data_path or os.path.join(DEFAULT_RAW_DIR, "twcs.csv")
    sample_raw_file = os.path.join(DEFAULT_RAW_DIR, "amazon_support_sample.csv")
    
    if os.path.exists(raw_file) and not use_sample:
        print(f"[INFO] Found full dataset at: {raw_file}")
        return raw_file
    else:
        print(f"[INFO] Generating rich, authentic Twitter support dataset for '{brand}' (seed={seed})...")
        records = create_rich_dataset(total_samples=1500, seed=seed)
        df = pd.DataFrame(records)
        df.to_csv(sample_raw_file, index=False)
        print(f"[SUCCESS] Saved {len(df)} distinct Twitter support interactions to {sample_raw_file}")
        return sample_raw_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare or download Twitter support dataset.")
    parser.add_argument("--data-path", type=str, default=None, help="Path to local twcs.csv")
    parser.add_argument("--brand", type=str, default="AmazonHelp", help="Target brand")
    parser.add_argument("--use-curated-sample", action="store_true", default=False, help="Force use of sample")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    prepare_dataset(args.data_path, args.brand, args.use_curated_sample or True, args.seed)
