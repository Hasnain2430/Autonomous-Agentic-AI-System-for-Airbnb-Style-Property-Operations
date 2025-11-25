✅ have to fix property host bot so that we can add property through telegram (DONE: /setup, /add_property, /help, /cancel all working)
✅ add data in the db so that we can check on the data (DONE: Run `python scripts/seed_dummy_data.py`)
<!-- guest inquiry works fine but the model hallucinates  -->
<!-- when booking guest inquiry we are just taking the name and bank ask for more details that are appropriate -->
guest booking payment mechanism from guest to host is not working, guest screenshot doesnt get sent to the host hence payment doesnt get confirmed and booking doesnt happen 
✅ remove price negotiation focus from everywhere fixed prices (DONE: All negotiation removed, fixed pricing only) 
✅ after booking QNA agent that will work during booking after booking etc questions like wifi available and generic questions from the DB, will be accessed by "/qna" (DONE: Hybrid QnA system implemented - checks database FAQs first, then LLM fallback)
✅ weekly reports sent to the host regarding property bookings payments number of guests (DONE: Weekly report system implemented with API endpoint)   
✅ what if we add fixed questions that are answered by the customer and extra questions are handled by the LLM (DONE: Fixed booking and payment questions implemented)
✅ dO Hybrid approach fixed QnA and LLM fallback (DONE: Fixed questions for booking/payment, LLM for general inquiries)
✅ during profile setup also ask for bank and bank account number from the host so that customers can transfer their money there (DONE: Added bank_name and bank_account steps to /setup flow)
✅ change the currency to pakistani rupees rather then dollars (DONE: Replaced all $ with PKR throughout the codebase)
✅ ask the host some basic questions such as does your property have wifi if yes what is the name and password, does it have air conditioning, does it have a TV installed in it? (DONE: Added amenity questions to /add_property flow - WiFi, AC, TV, parking, kitchen)