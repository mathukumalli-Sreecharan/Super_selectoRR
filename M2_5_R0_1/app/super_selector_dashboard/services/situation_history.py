"""Read-only derivation of synthetic entry and delivery-level states."""
from collections import defaultdict
from typing import Any

def batter_situation_rows(data: dict[str,Any], player_id: str) -> list[dict[str,Any]]:
    deliveries=data["delivery_records"]; rows=[]
    for s in data["player_situation_history"]:
        if s["discipline"]!="BAT" or s["player_id"]!=player_id: continue
        unknown=s.get("entry_state_status")=="UNKNOWN"
        faced=next((d for d in deliveries if d["delivery_id"]==s.get("first_faced_delivery_id")),None)
        score="UNKNOWN" if unknown or s.get("entry_score") is None else s["entry_score"]
        wickets="UNKNOWN" if unknown or s.get("wickets_at_entry") is None else s["wickets_at_entry"]
        overs="UNKNOWN" if unknown or s.get("overs_completed_at_entry") is None or s.get("balls_in_current_over_at_entry") is None else f"{s['overs_completed_at_entry']}.{s['balls_in_current_over_at_entry']}"
        rows.append({"Player":player_id,"Match":s["match_id"],"Competition":s.get("competition") or "NOT RECORDED","Season":s.get("season") or "NOT RECORDED","Innings":s["innings_id"],"Batting position":s.get("batting_position") if s.get("batting_position") is not None else "UNKNOWN","Entry score":score,"Wickets at entry":wickets,"Overs at entry":overs,"Entry reference":s.get("entry_sequence_ref") or "UNKNOWN","First faced delivery":s.get("first_faced_delivery_id") or "UNKNOWN","First faced state":(f"{faced['score_before']}/{faced['wickets_before']} after {faced['legal_balls_completed_before']//6}.{faced['legal_balls_completed_before']%6}" if faced else "UNKNOWN"),"Scenario candidate":s.get("entry_scenario_candidate") or "UNRESOLVED","Classification status":s.get("entry_classification_status") or "NOT VALIDATED","Reason / unresolved requirement":s.get("classification_reason") or s.get("unresolved_requirement") or "UNRESOLVED","Participation":s["participation_id"],"Source sequence":s.get("entry_sequence_ref") or "MISSING_REFERENCE"})
    return rows

def batter_performance_rows(data: dict[str,Any], player_id: str) -> list[dict[str,Any]]:
    part_ids={s["participation_id"] for s in data["player_situation_history"] if s["discipline"]=="BAT" and s["player_id"]==player_id}
    return [{"Delivery":d["delivery_id"],"Match":d["match_id"],"Innings":d["innings_id"],"Sequence":d["sequence"],"Performance state before delivery":f"{d['score_before']}/{d['wickets_before']} after {d['legal_balls_completed_before']//6}.{d['legal_balls_completed_before']%6}","Batter faced":d["batter_faced"],"Player":d["batter_id"]} for d in data["delivery_records"] if d["batter_id"]==player_id and d["batter_participation_id"] in part_ids]

def bowling_situation_rows(data: dict[str,Any], player_id: str) -> list[dict[str,Any]]:
    groups=defaultdict(list)
    for d in data["delivery_records"]:
        if d["bowler_id"]==player_id: groups[(d["match_id"],d["innings_id"],(d["sequence"]-1)//6)].append(d)
    out=[]
    for (match,innings,over),balls in sorted(groups.items()):
        first=min(balls,key=lambda x:x["sequence"]); part=next((p for p in data["participations"] if p["participation_id"]==first["bowler_participation_id"]),{}); match_info=next((m for m in data["matches"] if m["match_id"]==match),{})
        out.append({"Match":match,"Competition":match_info.get("competition","NOT RECORDED"),"Season":match_info.get("season","NOT RECORDED"),"Innings":innings,"Over (synthetic sequence)":over,"Score/wickets at opportunity start":f"{first['score_before']}/{first['wickets_before']}","Completed overs / balls":f"{first['legal_balls_completed_before']//6}.{first['legal_balls_completed_before']%6}","Assigned role":part.get("assigned_role") or "NOT RECORDED","Actual deliveries in fixture":len(balls),"Scenario candidate":"UNCLASSIFIED","Classification status":"UNCLASSIFIED","Evidence limitation":"Synthetic delivery sequence; no assigned-role source."})
    return out
