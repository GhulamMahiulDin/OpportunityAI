"""
Shared "extracted opportunity text -> saved, scored opportunity" pipeline.
Used by both the manual/paste Analyze page and the Gmail sync job so the
scoring logic only lives in one place.
"""
from models.opportunity import create_opportunity, save_scores, add_requirement, get_opportunity, get_requirements
from models.profile import get_profile
from services.scoring import (
    calculate_match_score, calculate_skill_match, calculate_eligibility,
    generate_recommendation, generate_why_apply, generate_things_to_consider
)
from services.urgency import calculate_urgency_score
from services.trust import calculate_trust_score
from services.completeness import calculate_completeness_score


def _compute_full_scores(extracted, profile):
    """
    Runs `extracted` opportunity data + a student `profile` through every
    scoring sub-system and returns the final scores dict ready for
    save_scores(). This is the single source of truth for scoring — both
    a brand-new analysis and a post-correction re-score call this.
    """
    profile = profile or {}

    skill_match_res = calculate_skill_match(extracted, profile)
    eligibility_res = calculate_eligibility(extracted, profile)
    urgency_res = calculate_urgency_score(extracted)
    trust_res = calculate_trust_score(extracted)
    completeness_res = calculate_completeness_score(extracted)

    temp_scores = {
        'skill_match': skill_match_res,
        'eligibility': eligibility_res,
        'urgency': urgency_res,
        'trust': trust_res,
        'completeness': completeness_res
    }

    match_res = calculate_match_score(extracted, profile, temp_scores)

    rec_res = generate_recommendation(
        match_res['score'],
        eligibility_res['status'],
        urgency_res['score'],
        trust_res['score'],
        completeness_res['score']
    )

    why_apply = generate_why_apply(extracted, profile, temp_scores)
    things_to_consider = generate_things_to_consider(extracted, profile, temp_scores)

    return {
        'match_score': match_res['score'],
        'match_reasons': match_res['reasons'],
        'eligibility_status': eligibility_res['status'],
        'eligibility_reasons': [c['detail'] for c in eligibility_res['checks']],
        'skill_match_required': skill_match_res['required_match'],
        'skill_match_preferred': skill_match_res['preferred_match'],
        'skill_details': skill_match_res,
        'urgency_score': urgency_res['score'],
        'urgency_label': urgency_res['label'],
        'trust_score': trust_res['score'],
        'trust_reasons': trust_res['reasons'],
        'completeness_score': completeness_res['score'],
        'completeness_details': completeness_res,
        'recommendation': rec_res['recommendation'],
        'recommendation_label': rec_res['label'],
        'recommendation_icon': rec_res['icon'],
        'why_apply': why_apply,
        'things_to_consider': things_to_consider,
        'days_remaining': urgency_res.get('days_remaining'),
        'trust_label': trust_res.get('label'),
        'trust_disclaimer': trust_res.get('disclaimer'),
        'eligibility_checks': eligibility_res.get('checks', []),
        'completeness_present': completeness_res.get('fields_present', 0),
        'completeness_total': completeness_res.get('total_fields', 11),
        'completeness_present_items': completeness_res.get('present', []),
        'completeness_missing_items': completeness_res.get('missing', [])
    }


def run_full_analysis(db, user_id, profile, student_id, extracted, source='manual'):
    """
    Persists `extracted` as an opportunity, runs it through the full
    scoring engine, and saves the resulting scores. Returns (opp_id, final_scores).
    """
    # Defensive: profile should always exist (login_required guarantees a
    # student_profiles row), but never let a missing/blank profile crash
    # scoring — just score against an empty profile instead.
    profile = profile or {}

    opp_id = create_opportunity(db, user_id, extracted, source=source)

    for skill in extracted.get('required_skills', []):
        add_requirement(db, opp_id, 'skill', skill, 'required')
    for skill in extracted.get('preferred_skills', []):
        add_requirement(db, opp_id, 'skill', skill, 'preferred')
    for doc in extracted.get('required_documents', []):
        add_requirement(db, opp_id, 'document', doc, 'required')

    final_scores = _compute_full_scores(extracted, profile)

    if student_id:
        save_scores(db, opp_id, student_id, final_scores)
    db.commit()

    return opp_id, final_scores


def _extracted_from_stored_opportunity(db, opportunity):
    """
    Rebuilds an `extracted`-shaped dict from what's actually persisted for
    an existing opportunity (its row + opportunity_requirements), so a
    re-score reflects any admin corrections. Note: a few free-text fields
    the original AI extraction produced (e.g. cgpa_requirement) aren't
    stored as their own columns and so can't be reconstructed here — this
    is an existing data-model limitation, not something new to re-scoring.
    """
    reqs = get_requirements(db, opportunity['id'])
    extracted = dict(opportunity)
    extracted['required_skills'] = [
        r['requirement_text'] for r in reqs
        if r['requirement_type'] == 'skill' and r['required_or_preferred'] == 'required'
    ]
    extracted['preferred_skills'] = [
        r['requirement_text'] for r in reqs
        if r['requirement_type'] == 'skill' and r['required_or_preferred'] == 'preferred'
    ]
    extracted['required_documents'] = [
        r['requirement_text'] for r in reqs if r['requirement_type'] == 'document'
    ]
    return extracted


def rescore_opportunity_for_all_students(db, opportunity_id):
    """
    Re-runs the existing scoring engine (the same one run_full_analysis
    uses) for every student who already has a score record for this
    opportunity, using its current (possibly just-corrected) data. Called
    after an admin corrects opportunity fields so scores never go stale.

    Reuses the project's one scoring pipeline rather than inventing a
    second system. Returns the number of students whose scores were
    recalculated.
    """
    opportunity = get_opportunity(db, opportunity_id)
    if not opportunity:
        return 0

    extracted = _extracted_from_stored_opportunity(db, opportunity)

    student_rows = db.execute(
        "SELECT DISTINCT student_id FROM opportunity_scores WHERE opportunity_id = ?",
        (opportunity_id,)
    ).fetchall()

    rescored = 0
    for row in student_rows:
        student_id = row[0]
        user_row = db.execute(
            "SELECT user_id FROM student_profiles WHERE id = ?", (student_id,)
        ).fetchone()
        if not user_row:
            continue

        profile = get_profile(db, user_row[0])
        if not profile:
            continue

        final_scores = _compute_full_scores(extracted, profile)
        save_scores(db, opportunity_id, student_id, final_scores)
        rescored += 1

    db.commit()
    return rescored
