# Beta Recruiting Kit — Redlight

Goal: 50 active drivers in two weeks. The metric that matters is **share-card export rate per session** (≥15% → the viral loop works; see `B2B-RESEARCH.md` for the fork). So recruiting copy should prime people to actually *use* it on real drives, not just poke around once.

---

## Who to recruit (in priority order)

1. **Daily commuters** — 20+ min of stop-and-go each way. They hit the most lights, see the biggest numbers, feel the product fastest.
2. **Rideshare / delivery drivers** — highest light exposure, most motivated by time. (Also your B2B beachhead — flag the keen ones.)
3. **People who text at lights** (they know who they are) — the behavior-change target.
4. **Friends with big group chats** — the share card only goes viral if early users have an audience.

Avoid: people who rarely drive, transit-only city dwellers. They can't generate signal.

---

## The recruiting message (DM / text — keep it short)

> Hey — I built a thing. It's called Redlight. It tells you how many months of your life you'll spend sitting at red lights, then turns paying attention into a daily streak game. Mounts on your dash, watches the light, chimes when it goes green so you keep your eyes up.
>
> I need ~50 people to beat on it for two weeks. You in? Takes 2 min to install. [link]

## The recruiting message (email)

**Subject:** Want to know how much of your life red lights are stealing?

```
Hey {{first_name}},

Quick one. I've been building an app called Redlight and I want you in the first beta.

The pitch: you'll spend MONTHS of your life stopped at red lights. Redlight makes that number real — and then turns looking up (instead of at your phone) into a daily streak you won't want to break. You mount your phone, it watches the light, and it chimes when the light goes green. It never asks you to touch the screen while you drive.

I need about 50 real drivers to use it on real commutes for two weeks. If you're in:

  1. Install: {{testflight_or_apk_link}}
  2. Do the 30-second onboarding (you have to confirm your phone is mounted)
  3. Use Camera Mode on your next few drives
  4. Tell me what's broken / confusing / good: {{feedback_form_link}}

That's it. No account, no ads, your camera + location never leave your phone.

Thanks for being an early one.
— {{your_name}}
```

## Social post (if you want broader reach)

```
You will spend ~3 months of your life sitting at red lights.

I built an app that makes that number real — then pays you back for looking up instead of at your phone.

Beta's open. 50 spots. Drivers only. 👇
{{link}}
```

---

## Tester one-pager (send after they install)

```
WELCOME TO THE REDLIGHT BETA

What this is: an attention-and-habit tracker for drivers. Not a self-driving anything. You still watch the road — always.

THE ONE RULE
Mount your phone before you drive. Never touch it while moving. The app is built so you never have to.

WHAT TO TRY (over the next 2 weeks)
□ Day 1: Run the calculator. Screenshot your lifetime number.
□ Day 1: Open Camera Mode while PARKED first, run a full cycle so you know the rhythm (red → green → "I see it").
□ Then: Use Camera Mode on 3+ real drives with the phone mounted.
□ Mid-week: Check your streak. Did the daily reminder fire at 8am?
□ Any time: Export a share card. Send it to someone.

WHAT WE'RE WATCHING FOR
- Does the green-light cue land at the right moment?
- Is anything confusing or annoying?
- Did you actually share your card? Why or why not?  ← this one matters most

REPORT ANYTHING
{{feedback_form_link}} — or just text me. Screenshots welcome. Brutal honesty preferred.

A heads-up: light detection and stop-tracking are SIMULATED in this beta (fixed timing, fake stops). We're testing the experience and the share loop first, real ML next. So if the "green" feels metronomic — that's why.
```

---

## Feedback form structure (Google Form / Tally / Typeform)

Keep it to 7 questions. Long forms kill response rate.

1. **How many drives did you use Camera Mode on?** (0 / 1–2 / 3–5 / 6+)  _— engagement check_
2. **Did the green-light cue feel well-timed?** (Too early / Just right / Too late / Didn't notice it)
3. **Did you export and share a card?** (Yes, to 1 person / Yes, to a group / No)  _— THE metric_
4. **If you didn't share — why not?** (free text)  _— the most valuable answer in the whole form_
5. **What was the single most confusing thing?** (free text)
6. **On a scale of 0–10, how likely are you to recommend Redlight to another driver?** (NPS)
7. **Anything else?** (free text)

Pipe responses into a sheet. Tag each respondent's share answer so you can compute share-rate against your PostHog `session_started` count.

---

## Logistics

- **iOS:** TestFlight public link (after Beta App Review). Up to 10,000 external testers.
- **Android:** the EAS internal-distribution APK link works with zero Play setup for the first 50. Send the URL; they tap install.
- **Cadence:** send the recruiting message, then the one-pager on install, then ONE nudge at day 4 ("how's it going? streak alive?") and ONE wrap-up at day 12 ("last push — please fill the form"). Don't over-message.
- **Incentive (optional):** "founding driver" credit in the app's About screen, or first dibs on the paid tier. Money isn't necessary for 50 friendly testers.

## Two-week timeline

| Day | Action |
| --- | --- |
| 0 | Send recruiting messages to ~80 people (expect ~60% install). |
| 0 | Auto-send the one-pager on install. |
| 4 | Nudge #1 — "streak still alive?" |
| 7 | Check PostHog: is share-rate trending toward 15%? |
| 12 | Nudge #2 — "last push, fill the form." |
| 14 | Close beta. Compute share-rate. Make the consumer-vs-fleet fork call. |
