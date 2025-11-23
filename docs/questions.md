# Project Implementation Questions

Please answer the following questions to help us create a detailed implementation plan. You can add your answers directly below each question.

---

## 1. Technology Stack & Development Environment

### 1.1 Programming Language Preference

**Question:** Which programming language would you prefer for implementing the agents and backend services?

- [ ] Python (recommended for AI/ML libraries)
- [ ] Node.js/TypeScript (good for n8n integration)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** Python ofc and for n8n java bcs that is what it works in

---

### 1.2 Agent Framework

**Question:** How would you like to implement the agents?

- [ ] LangChain/LangGraph (structured agent framework)
- [ ] AutoGen (multi-agent conversation framework)
- [ ] Custom implementation with direct LLM API calls
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** Langchain/LangGraph

---

### 1.3 LLM Provider

**Question:** Which LLM provider would you like to use?

- [ ] OpenAI (GPT-4, GPT-3.5)
- [ ] Anthropic (Claude)
- [ ] Local models (Ollama, LM Studio, etc.)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** Qwen and I will provide you with the api key when needed

**Follow-up:** Do you have API keys set up, or do you need help with that?

**Your Answer:**

---

## 2. Chat Platform Selection

### 2.1 Guest Interaction Channel

**Question:** Which chat platform would you like to use for guest interactions?

- [ ] Telegram Bot (easiest to set up, good for testing)
- [ ] WhatsApp Bot (requires Business API, more complex)
- [ ] Simple Web Chat (custom interface, full control)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** Telegram bot

**Follow-up:** If Telegram, do you have a Telegram account and are you comfortable creating a bot via BotFather?

**Your Answer:** I do not have a telegram account but I can make it its not that much difficult

---

## 3. Data Storage & Configuration

### 3.1 Configuration Storage

**Question:** How would you like to store host and property configuration?

- [ ] JSON files (simple, easy to edit)
- [ ] SQLite database (lightweight, structured)
- [ ] PostgreSQL/MySQL (if you need more robust storage)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** json files or sqlite database and keep in mind that i will also have the property photos and i think db is better

---

### 3.2 Booking & Log Storage

**Question:** How should we store booking records and system logs?

- [ ] Same as configuration (JSON files or database)
- [ ] Separate storage system
- [ ] n8n's built-in database
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** i dont understand what you mean by system logs, but for booking records same configuration (database)

---

## 4. n8n Setup

### 4.1 n8n Deployment

**Question:** How would you like to run n8n?

- [ ] Self-hosted (Docker/local installation)
- [ ] n8n Cloud (hosted service)
- [ ] Not sure - need recommendation

**Your Answer:** Self-hosted (Docker/local installation) i alr have docker set up and n8n set up

**Follow-up:** Are you familiar with Docker, or would you prefer a simpler installation method?

**Your Answer:** i alr have docker set up and n8n set up

---

### 4.2 n8n Integration Method

**Question:** How should agents communicate with n8n?

- [ ] HTTP webhooks (agents expose REST endpoints)
- [ ] n8n HTTP Request nodes calling agent APIs
- [ ] Direct function calls (if agents run in same environment)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** HTTP webhooks (agents expose REST endpoints) i assume use fast api or something idk choose whats best for this

---

## 5. Google Calendar Integration

### 5.1 Google Calendar Setup

**Question:** Do you have a Google account and are you comfortable setting up Google Calendar API credentials?

- [ ] Yes, I can set it up
- [ ] Yes, but I'll need guidance
- [ ] No, I'll need help with this

**Your Answer:** Since i will be acting as the host so yes i will share credentials but what happens if the host is someone else?

---

### 5.2 Calendar Access

**Question:** Should the system:

- [ ] Create events in a dedicated calendar for the project
- [ ] Use your personal calendar
- [ ] Create a new calendar specifically for property bookings

**Your Answer:** Create a new calendar specifically for property bookings

---

## 6. Payment Verification

### 6.1 Payment Verification Approach

**Question:** How should payment verification work?

- [ ] Fully simulated (mock screenshots, automatic approval for testing)
- [ ] Real verification (host manually reviews actual screenshots)
- [ ] Hybrid (simulated for testing, real for demo)

**Your Answer:** customer sends the screenshot to the telegram chat, the agent takes that ss and sends it to the host and asks it to verify, the host checks bank or whatever and replies with yes or no.

---

### 6.2 Host Payment Approval Channel

**Question:** How should the host approve/reject payments?

- [ ] Email with approval link
- [ ] Telegram/WhatsApp bot for host
- [ ] Web dashboard
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** Telegram/WhatsApp bot for host. same telegram bot msgs the host automatically with the screenshot provided by the user and asks for confirmation

---

## 7. Cleaner Simulation

### 7.1 Cleaner Simulation Approach

**Question:** How should cleaner availability and responses be simulated?

- [ ] Simple logic (always available during certain hours)
- [ ] Random simulation (random accept/decline)
- [ ] Rule-based (availability based on existing bookings)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** cleaner just replies with okay will clean. not gonna make this too much complex.

---

### 7.2 Cleaner Notification Method

**Question:** How should cleaners be notified (even if simulated)?

- [ ] Log entries only (no actual notifications)
- [ ] Email notifications (simulated)
- [ ] SMS/WhatsApp (if you want to test real notifications)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** Msg the cleaner on telegram to clean the place and ask for

---

## 8. Testing & Evaluation

### 8.1 Testing Approach

**Question:** How would you like to test the system?

- [ ] Manual testing with scripted conversations
- [ ] Automated test scripts
- [ ] Both manual and automated
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** this is on you as to how we will test the system and what sort of results will be generated from tests that we can put in the report

---

### 8.2 Evaluation Data

**Question:** Do you need help creating test scenarios and conversation scripts, or do you have specific scenarios in mind?

**Your Answer:** i dont mind you creating some scenarios for me

---

## 9. Project Timeline & Priorities

### 9.1 Timeline

**Question:** What is your project deadline, and how much time can you dedicate per week?

**Your Answer:** i have exactly 2 days to implement this. dont have much time

---

### 9.2 Implementation Priority

**Question:** Which features should we prioritize if we run short on time? (Rank 1-5, 1 = highest priority)

- [ ] Guest chat interface and basic inquiry handling
- [ ] Booking confirmation and payment workflow
- [ ] Google Calendar integration
- [ ] Issue handling during stays
- [ ] Cleaning coordination
- [ ] Summary reports

**Your Answer:** you can forget about the report for now that is not your concern. and i want the whole project to be ready in 2 days

---

## 10. Development Preferences

### 10.1 Code Organization

**Question:** Do you have any preferences for project structure?

- [ ] Monorepo (all code in one repository)
- [ ] Separate services (agents, n8n workflows, etc.)
- [ ] No preference

**Your Answer:** all code in one repo or folder but the repo/folder has sub folders

---

### 10.2 Documentation

**Question:** What level of documentation do you need?

- [ ] Code comments only
- [ ] README with setup instructions
- [ ] Comprehensive documentation (API docs, architecture diagrams, etc.)
- [ ] Other (please specify): **\*\***\_\_\_**\*\***

**Your Answer:** multiple readme that we will make and comprehensice documentation at the very end

---

## 11. Additional Considerations

### 11.1 Security & Privacy

**Question:** Are there any specific security or privacy requirements for your project?

- [ ] Basic security (API keys in environment variables)
- [ ] Enhanced security (encryption, secure storage)
- [ ] Compliance requirements (GDPR, etc.)
- [ ] No specific requirements

**Your Answer:** Enhanced security if possible and easy otherwise basic

---

### 11.2 Deployment

**Question:** Where do you plan to deploy/run this system?

- [ ] Local machine only (for development/testing)
- [ ] Cloud platform (AWS, Azure, GCP)
- [ ] VPS/server
- [ ] Not sure yet

**Your Answer:** local machine.

---

### 11.3 Additional Features

**Question:** Are there any additional features or modifications you'd like to add beyond what's in the project description?

**Your Answer:** none so far

---

## Notes Section

Use this space for any additional information, concerns, or requirements:

---

## Follow-up Questions

Please answer these additional questions to clarify a few important details:

### F1. n8n Technology Clarification

**Question:** You mentioned "for n8n java bcs that is what it works in" - just to clarify, n8n is actually built with Node.js/TypeScript, not Java. The agents will be in Python (as you specified), and they'll communicate with n8n via HTTP webhooks. n8n workflows will be configured through its web UI. Is this understanding correct, or did you mean something else?

**Your Answer:** yes what u eexplained is correct.

---

### F2. System Logs Explanation

**Question:** By "system logs," I mean records of all actions the system takes - like when a guest sends a message, when an agent makes a decision, when a booking is confirmed, when cleaning is scheduled, etc. These logs help with debugging and generating reports. Since you mentioned skipping reports for now, should we still log these events (for future use) or skip logging entirely?

**Your Answer:** yes okay store system logs

---

### F3. Cleaner Notification (Incomplete Answer)

**Question:** Your answer for cleaner notification seems incomplete: "Msg the cleaner on telegram to clean the place and ask for" - could you complete this? Should the cleaner:

- Just receive a message and automatically reply "okay will clean"?
- Receive a message and reply with confirmation?
- Something else?

**Your Answer:** Just receive a message and automatically reply "okay will clean"? and then will update when cleaned so we can update our system. keep in mind that the host will enter the cleaner details at the start when entering info aobut the property.

---

### F4. Google Calendar - Multiple Hosts

**Question:** You asked "what happens if the host is someone else?" - For this project, we'll design it so that:

- Each host configuration includes their Google Calendar credentials
- The system uses the host's credentials from the configuration to create calendar events
- If you're the only host for now, we'll use your credentials, but the system will be designed to support multiple hosts

Does this approach work for you?

**Your Answer:** okay

---

### F5. Property Photos Storage

**Question:** You mentioned you'll have property photos. How should we handle these?

- Store file paths in the database and keep photos in a folder?
- Store photos as base64 in the database (not recommended for large files)?
- Store photos in cloud storage (S3, etc.) and save URLs in database?
- Just file paths for now (photos in a local folder)?

**Your Answer:** Just file paths for now (photos in a local folder)?

---

### F6. Qwen API Details

**Question:** For Qwen API:

- Do you have the API key ready, or will you provide it later?
- Which Qwen model/service are you using? (Qwen via DashScope/Alibaba Cloud, or another provider?)
- Do you know the API endpoint and format?

**Your Answer:** i have the key and i will provide it later when you ask me for it. the model i will also tell later and also provide with code snipet on how we can use the api

---

### F7. Telegram Bot Setup

**Question:** Since you don't have a Telegram account yet:

- Will you create the account and bot yourself, or do you want step-by-step instructions?
- Should we design the system to work with a single bot that handles both guests and host (using different chat IDs), or separate bots?

**Your Answer:**i will create account on my own but creating the bot is where i need ur help and two different bots

---

### F8. FastAPI Confirmation

**Question:** You mentioned FastAPI - that's perfect for this! We'll use FastAPI to create REST endpoints that n8n can call. The agents will be Python functions/classes that FastAPI endpoints invoke. Does this sound good?

**Your Answer:** perfect

---

### F9. Timeline Reality Check

**Question:** You have 2 days to implement. This is very tight. To make this realistic, I'm thinking:

- **Day 1:** Core booking flow (inquiry → booking → payment verification → calendar)
- **Day 2:** Issue handling, cleaning coordination, testing

We'll skip or heavily simplify:

- Host Summary Agent (reports) - as you mentioned
- Complex error handling
- Extensive testing automation

Does this prioritization work, or do you want to adjust it?

**Your Answer:** no i want to implement exactly what i wrote in the @project description md

---

### F10. Telegram Bot - Guest vs Host Identification

**Question:** For the Telegram bot, how should we distinguish between guest messages and host messages?

- Option A: Same bot, different chat IDs (system tracks which chat ID is the host)
- Option B: Host uses a special command or keyword to identify themselves
- Option C: Separate Telegram bots (one for guests, one for host)

Which approach do you prefer?

**Your Answer:** seperate telegram bots. the host one, we can use that to get info from the host about the property and the images and then write back to it when needed during payment of summeries. and the customer one is for customer. is creating telegram bots free or will that be free?

**Note:** Yes, creating Telegram bots is completely free! You just need a Telegram account and use BotFather to create bots. There are no costs involved.

---

**Once you've answered these follow-up questions, we'll create a summary README to confirm we're on the same page.**
