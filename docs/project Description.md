# Autonomous Airbnb Property Operations Manager

This document describes the full concept of your Agentic AI project from start to finish. You can give this to Cursor so it understands what system you want to build and why. It focuses on what the system does and why each part exists, not on low level technical details.

---

## 1. Problem Background and Motivation

Short term rental hosts for platforms like Airbnb handle a lot of repetitive digital work

• Answering guest questions about availability, price, facilities and rules
• Deciding whether to accept a booking and sometimes negotiating price
• Sending check in and check out instructions at the right time
• Handling issues during stays such as wifi problems or missing items
• Planning and scheduling cleaning before and after each stay
• Manually tracking bookings in personal calendars and notes
• Reviewing how the property performed over a week or month

Most hosts do all of this manually through messaging apps and simple templates.
This is time consuming, error prone, and stressful, especially with multiple guests and overlapping dates.

There is a clear opportunity for an autonomous system that

• Understands guest messages
• Makes decisions based on host rules
• Coordinates different tasks like booking, cleaning, and issue handling
• Keeps the host informed without requiring constant manual work

This is exactly the kind of complex, open ended, real world problem that fits an Agentic AI project.

---

## 2. Goal of the System

Build an autonomous, multi agent system that manages the digital operations for up to three Airbnb style properties owned by a single host.

The system should

• Communicate with guests through a chat channel
• Handle booking conversations, basic negotiation, and confirmation
• Manage payment proof and involve the host only for final payment approval
• Trigger cleaning workflows before and after stays
• Handle common issues during stays with minimal host involvement
• Record confirmed bookings into Google Calendar for the host
• Generate weekly and monthly summary reports for each property

The system must act autonomously once the host has provided initial configuration and payment approvals.

---

## 3. High Level Architecture

At a high level, the system has four main parts

1. Host and property configuration
2. Guest interaction channel
3. Agent layer
4. n8n orchestration and logging

### 3.1 Host and property configuration

The host provides information once about themselves and up to three properties.
This configuration is stored in a simple and persistent format, for example JSON or a small database.

For the host

• Name
• Contact email
• Contact phone or messaging handle for alerts
• Preferred language

For each property

• Property identifier
• Name and general location
• Base nightly price
• Minimum and maximum acceptable price for negotiation
• Maximum number of guests
• Check in and check out times
• Cleaning rules such as when to clean around bookings
• Template for check in instructions
• Template for check out instructions

This configuration is the main source of truth for all agents.

### 3.2 Guest interaction channel

Guests interact with the system through a single messaging channel, for example

• Telegram bot
• WhatsApp bot
• Simple web chat

To the guest, it looks like a normal chat with a virtual assistant for the property.

### 3.3 Agent layer

The core intelligence of the system lives in several focused agents

• Inquiry and Booking Agent
• Issue Handling Agent
• Cleaner Coordination Agent
• Host Summary Agent

Each agent

• Receives structured input from n8n
• Uses host and property rules as context
• Decides what to do next and what to reply
• Returns a structured output back to n8n

### 3.4 n8n orchestration and logging

n8n is used as the central workflow engine

• Receives and sends chat messages
• Routes tasks to the correct agent
• Manages timelines and delayed actions
• Integrates with Google Calendar
• Triggers periodic summary generation
• Stores logs for all actions and events

n8n provides autonomy at the workflow level, while agents provide autonomy at the reasoning and decision level.

---

## 4. Actors and Roles

There are three main human or external actors

1. Host
2. Guest
3. Cleaner (simulated or very simple external contact)

### Host

• Configures properties once at the start
• Confirms or rejects payment proofs
• Receives escalation messages for serious issues
• Receives weekly and monthly summary reports
• Views bookings in Google Calendar

### Guest

• Asks about availability, price, and property details
• Requests booking
• Sends payment screenshot
• Receives booking confirmation and instructions
• Reports issues during stay

### Cleaner

In this project, the cleaner is treated in a very simple way

• Receives cleaning assignment notifications
• Is assumed to accept or decline based on simple logic or simulation

---

## 5. Agents and Their Responsibilities

### 5.1 Inquiry and Booking Agent

Focus
Manages all guest interactions before booking and around payment.

Main responsibilities

• Understand guest messages about availability and property details
• Use property configuration to check if requested dates are available based on a simple rule
• Provide clear information about price, number of nights, and basic rules
• Negotiate price within the minimum and maximum range defined by the host
• When guest wants to proceed, explain booking steps including payment method and amount
• Ask the guest to upload a payment screenshot as proof
• Inform the guest that payment is under verification
• Pass payment details to the host for final confirmation
• After host confirms payment, mark booking as confirmed and generate booking record
• Trigger follow up actions, such as sending confirmation message and notifying other agents through n8n

The Inquiry and Booking Agent does not directly manipulate calendars or cleaning.
Instead it requests that n8n run those workflows once a booking is confirmed.

### 5.2 Issue Handling Agent

Focus
Deals with any message that looks like an issue during the guest stay.

Main responsibilities

• Receive messages that are not simple booking questions during an active stay
• Classify the issue into categories such as
• Simple question or FAQ
• Cleaning or missing item related
• Urgent or serious escalation
• For FAQ type issues, respond directly with relevant information from property configuration, for example wifi instructions
• For cleaning and missing item issues, forward a structured task to Cleaner Coordination Agent and inform the guest that the issue is being handled
• For urgent or unresolved issues, escalate to host by passing a clear summary to n8n, which then contacts the host on a separate channel

The Issue Handling Agent allows most problems to be handled without host involvement, while still respecting safety for serious cases.

### 5.3 Cleaner Coordination Agent

Focus
Manages cleaning tasks related to bookings and cleanliness complaints.

Main responsibilities

• When a booking is confirmed, schedule two cleaning tasks for that property
• One before check in if needed
• One after check out
• For cleanliness issues during a stay, decide whether to send a cleaner or suggest an alternative such as leaving extra towels in a certain place, based on property rules
• Provide simulated cleaner availability checks, for example always available between certain hours or based on simple conditions
• Inform n8n about scheduled cleanings so they can be logged and included in reports
• If cleaning cannot be scheduled, notify the host via n8n so the host can take manual action

### 5.4 Host Summary Agent

Focus
Generates weekly and monthly reports for the host based on system logs.

Main responsibilities

• Run on a schedule such as once a week and once a month
• Use logs collected by n8n to gather events for a given time period
• Group information by property
• Produce a clear report for each property that includes
• Date range
• Number of booking requests and number actually confirmed
• Total nights booked versus free
• Number of issues reported by guests and how they were resolved
• Number of escalations to the host
• Number of cleaning tasks scheduled and completed
• Any failures or unusual patterns observed
• Format reports as readable messages or simple PDF files
• Return these to n8n so that n8n can deliver them to the host through email or messaging

This agent adds a strong evaluation and monitoring component to the system and is also useful for the experimental and results sections of your paper.

---

## 6. End to End Guest Journey

This section describes an example journey for a single booking, from first message to final summary.

### 6.1 Inquiry stage

1. Guest sends a message asking if a property is available for certain dates.
2. n8n receives the message through the chat integration and decides it is a new conversation.
3. n8n forwards the message plus property context to the Inquiry and Booking Agent.
4. The agent checks rules and decides whether the dates are acceptable.
5. The agent replies with availability information, price, and any basic conditions.
6. n8n sends this reply to the guest.

### 6.2 Booking confirmation and payment

1. The guest replies that they want to book.
2. Inquiry and Booking Agent calculates final price and explains the booking steps, including payment method.
3. The agent asks the guest to upload a payment screenshot and tells them that the booking will be confirmed after verification.
4. The guest uploads the screenshot.
5. n8n stores the screenshot and forwards a structured summary to the host through the host channel.
6. The host reviews the screenshot and responds with yes or no.
7. n8n passes this approval back into the booking workflow.

If payment is approved

• Inquiry and Booking Agent marks booking as confirmed
• n8n creates a booking record
• n8n creates an event in Google Calendar for the host, including dates and guest name
• n8n triggers cleaning workflows through the Cleaner Coordination Agent
• n8n sends a confirmation message to the guest

If payment is not approved

• The agent informs the guest that the payment could not be confirmed
• The booking is not recorded and no cleaning or calendar action is taken

### 6.3 Pre check in

1. Before the check in date, n8n triggers a pre check in workflow at a suitable time, for example one day before.
2. n8n fetches check in instructions from the property configuration.
3. The system sends these instructions and the exact property location to the guest.
4. Cleaner Coordination Agent is reminded of the upcoming check in cleaning if needed.

### 6.4 During stay

1. If the guest sends a question or complaint during their stay, n8n checks whether it is tied to an active booking.
2. n8n routes the message to the Issue Handling Agent.
3. The agent classifies the problem and chooses an action
   • For FAQ, send a direct answer
   • For cleaning or missing item, send a request to the Cleaner Coordination Agent
   • For urgent issues, ask n8n to alert the host
4. Guest receives feedback about what is being done.

### 6.5 Check out and after

1. On the check out date, n8n sends check out instructions from the property configuration.
2. Cleaner Coordination Agent schedules or confirms post check out cleaning.
3. All actions are logged in n8n for future summaries.

---

## 7. Google Calendar Integration

The system uses Google Calendar only for one simple and clear purpose

Record confirmed bookings for the host.

When a booking is confirmed

• n8n creates a calendar event on the host calendar using the host configured calendar account
• The event contains
• Property name
• Guest name or identifier
• Start and end dates and times
• Short description of payment status and any special notes

This allows the host to quickly see occupancy and avoid double booking, while keeping the implementation light and focused.

---

## 8. Logging and Metrics

Throughout all workflows, n8n logs key actions such as

• Guest messages
• Agent decisions
• Booking confirmations and cancellations
• Cleaning tasks scheduled and executed
• Escalations to host
• Calendar events created

These logs serve two purposes

1. Allow debugging and monitoring of the system
2. Provide data for evaluation and for the Host Summary Agent

Metrics that can be calculated include

• Number of booking requests and confirmation rate
• Average time to respond to initial inquiries
• Issue resolution rate without host intervention
• Number of escalations per week
• Cleaning tasks per booking

These metrics are important for the research and evaluation part of your project.

---

## 9. Evaluation and Experiments

For the research paper and for practical testing, you can design experiments that simulate various scenarios

• Normal successful booking flow with payment approval
• Payment rejected or delayed scenarios
• Multiple overlapping booking requests for similar dates
• Guests with several questions and negotiation steps
• Issues such as wifi problems, missing items, and cleanliness complaints
• Failure simulation for cleaner not available or workflow error

For each experiment

• Run a scripted or semi scripted conversation
• Let the system handle it autonomously
• Use logs and calendar entries to check whether the system behavior matches the expected outcome

Then use these results to report

• Success rates
• Edge cases where the system fails or needs improvement
• Insights about how agent responsibilities and orchestration affect performance

---

## 10. Ethical and Practical Considerations

Several ethical and practical points should be discussed in your paper and considered in your design

• Privacy of guest data and messages
• Secure storage of any payment related screenshots, even in a simulated form
• Transparency to guests that they are interacting with an automated system
• Fair negotiation that stays within limits set by the host
• Clear escalation paths where serious issues are always brought to human attention
• Avoiding deceptive behavior, such as promising actions the system cannot perform

These considerations show that you are treating Agentic AI as a professional tool, not a toy.

---

## 11. Summary

This project builds a realistic, autonomous operations manager for up to three properties owned by a single host. The system uses multiple agents coordinated by n8n to handle booking conversations, payment verification, cleaning coordination, issue handling, calendar recording, and periodic reporting.

The host configures the system once and then only needs to approve payments and handle rare escalations. Guests interact through a single chat channel and see a smooth experience from inquiry to check out.

This design satisfies the course requirements for a complex computing problem, uses Agentic AI in a meaningful way, and remains implementable within your available time by delegating detailed coding tasks to tools like Cursor.