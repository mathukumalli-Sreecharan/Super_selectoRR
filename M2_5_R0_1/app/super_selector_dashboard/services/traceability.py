"""Evidence-chain drill-down for synthetic decisions."""
from typing import Any

def evidence_chain(data: dict[str,Any], decision_id: str) -> list[dict[str,Any]]:
    decision=next((x for x in data["decisions"] if x["decision_id"]==decision_id),None)
    if decision is None: return [{"Step":"Decision","Reference":decision_id,"Resolution":"MISSING_REFERENCE"}]
    chain=[{"Step":"Decision","Reference":decision_id,"Resolution":"RESOLVED","State":decision.get("decision_status"),"Player":decision.get("player_id")}]
    metrics={m["metric_evidence_id"]:m for m in data["metrics"]}
    classes={c["classification_id"]:c for c in data["scenario_classifications"]}
    opps={o["opportunity_id"]:o for o in data["opportunities"]}
    events={e["event_id"]:e for e in data["events"]}
    records={r["source_record_id"]:r for r in data["source_records"]}
    ready={r["readiness_record_id"]:r for r in data["readiness_records"]}
    for metric_id in decision.get("supporting_metric_refs",[]):
        m=metrics.get(metric_id)
        chain.append({"Step":"Metric evidence","Reference":metric_id,"Resolution":"RESOLVED" if m else "MISSING_REFERENCE","Player":m.get("player_id") if m else None,
          "Readiness":ready.get(m.get("readiness_record_id"),{}).get("status","MISSING_REFERENCE") if m else "MISSING_REFERENCE",
          "Metric ID":m.get("metric_id") if m else None,"Metric version":m.get("metric_version") if m else None,
          "Assessment reference":m.get("reliability_assessment_id") if m else "MISSING_REFERENCE",
          "Known limitations":m.get("label") if m else "Metric reference not found"})
        if not m: continue
        scenario_refs=m.get("scenario_classification_refs",[])
        for class_id in scenario_refs or [None]:
            c=classes.get(class_id) if class_id else None
            chain.append({"Step":"Scenario classification","Reference":class_id or "MISSING_REFERENCE","Resolution":"RESOLVED" if c else "MISSING_REFERENCE","Scenario":c.get("scenario_id") if c else None,"Status":c.get("classification_outcome") if c else None})
            if not c: continue
            op=opps.get(c.get("opportunity_id"))
            chain.append({"Step":"Player opportunity","Reference":c.get("opportunity_id") or "MISSING_REFERENCE","Resolution":"RESOLVED" if op else "MISSING_REFERENCE","Player":op.get("player_id") if op else None,"Participation":op.get("participation_id") if op else None})
            if not op: continue
            event=events.get(op.get("event_id"))
            chain.append({"Step":"Match event","Reference":op.get("event_id") or "MISSING_REFERENCE","Resolution":"RESOLVED" if event else "MISSING_REFERENCE","Match":event.get("match_id") if event else None,"Source event":event.get("delivery_ref") if event else None})
            refs=(event or {}).get("source_record_refs",[])
            if not refs: chain.append({"Step":"Source record","Reference":"MISSING_REFERENCE","Resolution":"MISSING_REFERENCE"})
            for ref in refs: chain.append({"Step":"Source record","Reference":ref,"Resolution":"RESOLVED" if ref in records else "MISSING_REFERENCE"})
    if not decision.get("supporting_metric_refs"):
        chain.append({"Step":"Metric evidence","Reference":"NO_SUPPORTING_METRIC_REFERENCE","Resolution":"NOT PROVIDED"})
        for class_id in decision.get("supporting_scenario_refs",[]):
            c=classes.get(class_id)
            chain.append({"Step":"Scenario classification","Reference":class_id,"Resolution":"RESOLVED" if c else "MISSING_REFERENCE","Scenario":c.get("scenario_id") if c else None,"Status":c.get("classification_outcome") if c else None,"Known limitation":"Decision refers to this scenario without a linked metric evidence record."})
    return chain
