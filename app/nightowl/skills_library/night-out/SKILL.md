---
name: night-out
description: "Plan a night out: check calendar availability, search restaurants, compare options, make reservations. Spawns parallel child agents for calendar + restaurant search."
metadata:
  { "nightowl": { "emoji": "🌙", "category": "lifestyle" } }
---

# Night Out Planner

Plan a complete night out for the user — from checking their calendar to booking a restaurant.

## When to Use

Use this skill when the user asks to:
- Plan a night out, dinner, or evening
- Find restaurants and check availability
- Coordinate a group outing

## Strategy

1. **Spawn two children in parallel:**
   - **Calendar child**: Check the user's calendar for conflicts on the requested date using `composio_execute` with Google Calendar tools
   - **Restaurant child**: Search for restaurants matching the criteria (location, cuisine, party size) using `composio_execute` with web search tools

2. **Wait for both completions** (do NOT poll)

3. **Synthesise results:**
   - If calendar shows conflicts, inform the user and suggest alternatives
   - Present the top 3-5 restaurant options with: name, cuisine, rating, price range, availability
   - Format as a clear comparison

4. **Get user's choice**, then:
   - If the restaurant supports online booking, use `composio_execute` to make the reservation (this will trigger HITL approval since it's a high-risk action)
   - Confirm the booking details back to the user

## Important Rules

- Always check calendar FIRST before suggesting times
- Never make a reservation without explicit user confirmation
- Present options clearly — the user is probably on their phone
- If party size > 6, mention that large group reservations may need a phone call
- Include approximate price per person when available

## Example Interaction

User: "Plan a night out for 4 this Saturday near the CBD"

1. Spawn calendar-check child → "Saturday evening is free"
2. Spawn restaurant-search child → "Found 5 options near CBD"
3. Present options to user
4. User picks one → request HITL approval → make reservation
5. Confirm booking
