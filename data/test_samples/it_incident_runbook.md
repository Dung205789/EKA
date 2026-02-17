# IT Incident Response Runbook

## Severity Levels
- SEV-1: Critical outage affecting all users
- SEV-2: Major degradation affecting many users
- SEV-3: Minor issue with workaround available

## Response Targets
- Acknowledge SEV-1 within 5 minutes
- Acknowledge SEV-2 within 15 minutes
- Acknowledge SEV-3 within 60 minutes

## Escalation Matrix
- First responder: On-call engineer
- If unresolved after 20 minutes (SEV-1), escalate to Incident Commander
- If unresolved after 45 minutes (SEV-1), escalate to CTO

## Communication
- Post updates every 15 minutes for SEV-1
- Post updates every 30 minutes for SEV-2
- Final incident report due within 48 hours

## Postmortem Requirements
- Include timeline, root cause, impact, and corrective actions
- Assign owner and due date for each action item

