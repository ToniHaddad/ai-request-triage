"""Eight requests a humanitarian organization in Lebanon could really receive. Synthetic data:
every name and figure is invented."""

SEED = [
    dict(team="Facilities", office="Head office", title="Rental contract end reminders",
         description="Remind the facilities team three months before each rental contract ends, "
                     "from the sheet that lists every rented centre, health centre and warehouse.",
         per_week=2, people=2, minutes=45, owner="Hala Mansour", data_class="internal",
         success_text="No contract ends without a reminder sent at least three months before.",
         success_measurable=True, existing_tool="partly", task_kind="fixed_rules", consequence="medium", systems=2),
    dict(team="Procurement", office="Head office", title="Purchase order rows into the stock system",
         description="Push approved purchase order rows from the procurement sheet into the stock "
                     "system, which accepts or rejects each row with a reason.",
         per_week=10, people=3, minutes=20, owner="Karim Daher", data_class="internal",
         success_text="Rows entered by hand fall from about 150 a month to under 10.",
         success_measurable=True, existing_tool="no", task_kind="fixed_rules", consequence="medium", systems=2),
    dict(team="Supply Chain", office="Warehouse network", title="Which procedure applies?",
         description="Warehouse keepers across forty warehouses and several donor projects ask which "
                     "receiving, dispatch or damage procedure applies. Answers must cite the current "
                     "procedure and the donor project's rule.",
         per_week=2, people=80, minutes=12, owner="Samir Khoury", data_class="internal",
         success_text="Procedure questions sent to the operations managers fall by half in 90 days.",
         success_measurable=True, existing_tool="partly", task_kind="language", consequence="medium", systems=2),
    dict(team="Programmes", office="Head office", title="Summaries of long meetings",
         description="Summaries and action lists after long coordination and steering meetings.",
         per_week=3, people=25, minutes=30, owner="Rima Haddad", data_class="internal",
         success_text="Minutes go out the same day instead of two days later, checked monthly.",
         success_measurable=True, existing_tool="yes", task_kind="language", consequence="low", systems=1),
    dict(team="Grants and Reporting", office="Head office", title="Donor report narrative from stock figures",
         description="Draft the narrative of a donor report from stock and distribution figures "
                     "held in the stock system.",
         per_week=1, people=7, minutes=180, owner="Nour Awad", data_class="internal",
         success_text="First draft within two days, with no figure that differs from the stock ledger.",
         success_measurable=True, existing_tool="no", task_kind="mixed", consequence="medium", systems=3),
    dict(team="Emergency Operations Room", office="Operations room", title="Operations room chat into a situation update",
         description="During an emergency, turn the room's chat (shelter needs, dispatches, "
                     "confirmations, cancellations) into a situation update.",
         per_week=3, people=6, minutes=40, owner="Tarek Nasr", data_class="personal",
         success_text="A situation update within 30 minutes of each request, checked against the chat.",
         success_measurable=True, existing_tool="partly", task_kind="language", consequence="high", systems=2),
    dict(team="Protection", office="Field centres", title="Protection case-note triage",
         description="Sorting incoming protection case notes by urgency and referral type.",
         per_week=10, people=12, minutes=15, owner="Dalia Frem", data_class="sensitive",
         success_text="Urgent cases reach a caseworker within four hours, audited weekly.",
         success_measurable=True, existing_tool="no", task_kind="language", consequence="high", systems=3),
    dict(team="Communications", office="Head office", title="Ask-anything intranet assistant",
         description="A general assistant on the intranet that answers any staff question.",
         per_week=2, people=200, minutes=5, owner="", data_class="internal",
         success_text="", success_measurable=False, existing_tool="no", task_kind="language",
         consequence="low", systems=1),
]
