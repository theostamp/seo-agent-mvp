import streamlit as st
import requests
from datetime import datetime

API_URL = "http://api:8000"

# Available WordPress sites
SITES = {
    "E-Therm": "https://e-therm.gr",
    "Oikonrg": "https://oikonrg.gr",
}

st.set_page_config(
    page_title="SEO Agent",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 SEO Agent MVP")
st.markdown("Ανάλυση περιεχομένου και προτάσεις βελτίωσης για WordPress sites")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Ρυθμίσεις")

    # Site selector
    selected_site = st.selectbox(
        "🌐 WordPress Site",
        options=list(SITES.keys()),
        index=0,
        help="Επέλεξε το site για ανάλυση"
    )
    site_url = SITES[selected_site]

    st.caption(f"URL: {site_url}")

    st.divider()
    api_url = st.text_input("API URL", value=API_URL)

    st.divider()
    st.markdown("### Πληροφορίες")
    st.markdown("""
    **Τι κάνει:**
    1. Keyword discovery με AI
    2. Διαβάζει το site σου
    3. Βρίσκει gaps
    4. Προτείνει βελτιώσεις
    """)

# Session state for preview
if "preview_proposal_id" not in st.session_state:
    st.session_state.preview_proposal_id = None
if "generated_html_result" not in st.session_state:
    st.session_state.generated_html_result = None


def update_proposal_status(api_url: str, proposal_id: int, status: str) -> None:
    try:
        response = requests.patch(
            f"{api_url}/proposals/{proposal_id}/status",
            json={"status": status},
            timeout=10,
        )
        if response.status_code == 200:
            st.toast(f"Proposal {proposal_id}: {status}")
            st.rerun()
        else:
            st.error(f"Σφάλμα αλλαγής status: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        st.error("Δεν μπορώ να συνδεθώ στο API")
    except Exception as e:
        st.error(f"Σφάλμα αλλαγής status: {str(e)}")


# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Νέα Ανάλυση",
    "📋 Proposals",
    "🔍 Preview",
    "📊 Site Audit",
    "🏠 Αρχική Σελίδα",
])

# Tab 1: New Analysis
with tab1:
    st.header("Νέα Ανάλυση")

    col1, col2 = st.columns(2)

    with col1:
        category_name = st.text_input(
            "Κατηγορία θέματος *",
            placeholder="π.χ. Επισκευή όψεων κτιρίων",
            help="Η κύρια κατηγορία για την οποία θέλεις ανάλυση"
        )

        location = st.text_input(
            "Τοποθεσία",
            placeholder="π.χ. Αθήνα",
            help="Προαιρετικά, για τοπικό SEO"
        )

    with col2:
        seed_keywords_text = st.text_area(
            "Seed Keywords",
            placeholder="επισκευή όψεων\nαποκατάσταση προσόψεων\nβάψιμο κτιρίων",
            help="Ένα keyword ανά γραμμή",
            height=120
        )

    if st.button("🔍 Εκτέλεση Ανάλυσης", type="primary", use_container_width=True):
        if not category_name:
            st.error("Παρακαλώ συμπλήρωσε την κατηγορία θέματος")
        else:
            seed_keywords = [kw.strip() for kw in seed_keywords_text.split("\n") if kw.strip()]

            payload = {
                "category_name": category_name,
                "seed_keywords": seed_keywords,
                "location": location if location else None,
                "objective": "suggest_improvements",
                "site_url": site_url,
            }

            with st.spinner("Εκτελείται η ανάλυση... (μπορεί να πάρει 1-2 λεπτά)"):
                try:
                    response = requests.post(
                        f"{api_url}/workflow/run",
                        json=payload,
                        timeout=180
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Ανάλυση ολοκληρώθηκε!")

                        # Metrics row 1
                        col1, col2, col3, col4 = st.columns(4)
                        keywords = result.get("discovered_keywords") or []
                        proposals = result.get("proposals") or []
                        col1.metric("Keywords", len(keywords))
                        col2.metric("Clusters", result.get("clusters_count", 0) or 0)
                        col3.metric("Σελίδες Site", result.get("site_pages_found", 0) or 0)
                        col4.metric("Proposals", len(proposals))

                        # Metrics row 2 - Analysis summaries
                        yoast = result.get("yoast_summary") or {}
                        schema = result.get("schema_summary") or {}
                        topology = result.get("topology") or {}

                        if yoast or schema or topology:
                            col1, col2, col3 = st.columns(3)
                            if yoast:
                                col1.metric(
                                    "Yoast Issues",
                                    yoast.get("total_issues", 0),
                                    delta=f"-{yoast.get('high_priority_issues', 0)} high" if yoast.get('high_priority_issues') else None,
                                    delta_color="inverse"
                                )
                            if schema:
                                ai_score = schema.get("ai_readiness_score") or 0
                                col2.metric(
                                    "AI Readiness",
                                    f"{ai_score}%",
                                    delta="Χαμηλό" if ai_score < 50 else "Καλό" if ai_score >= 75 else "Μέτριο"
                                )
                            if topology:
                                col3.metric(
                                    "Pillars / Satellites",
                                    f"{topology.get('pillars_count', 0)} / {topology.get('satellites_count', 0)}"
                                )

                        # Keywords found
                        if keywords:
                            with st.expander("🔑 Keywords που βρέθηκαν", expanded=True):
                                st.write(", ".join(keywords))

                        # Proposals
                        if proposals:
                            st.subheader("📝 Proposals")
                            for i, prop in enumerate(proposals, 1):
                                with st.expander(f"{i}. {prop['target_title']} ({prop['proposal_type']})"):
                                    st.markdown(f"**Τύπος:** `{prop['proposal_type']}`")
                                    st.markdown(f"**Περίληψη:** {prop['summary']}")
                                    if prop.get('outline'):
                                        st.markdown("**Outline:**")
                                        st.text(prop['outline'])
                                    if prop.get('suggested_schema'):
                                        st.markdown(f"**Schema:** `{prop['suggested_schema']}`")
                    else:
                        st.error(f"Σφάλμα: {response.status_code} - {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Δεν μπορώ να συνδεθώ στο API. Βεβαιώσου ότι τρέχει.")
                except requests.exceptions.Timeout:
                    st.error("❌ Timeout - η ανάλυση πήρε πολύ χρόνο")
                except Exception as e:
                    st.error(f"❌ Σφάλμα: {str(e)}")

# Tab 2: View Proposals
with tab2:
    st.header("Αποθηκευμένα Proposals")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Ανανέωση", use_container_width=True):
            st.rerun()

    # Filter
    status_filter = st.selectbox(
        "Φιλτράρισμα κατά status",
        ["Όλα", "needs_review", "approved", "rejected"],
        index=0
    )

    try:
        params = {}
        if status_filter != "Όλα":
            params["status"] = status_filter

        response = requests.get(f"{api_url}/proposals", params=params, timeout=10)

        if response.status_code == 200:
            proposals = response.json()

            if proposals:
                st.info(f"Βρέθηκαν {len(proposals)} proposals")

                for prop in proposals:
                    status_emoji = {
                        "needs_review": "🟡",
                        "approved": "🟢",
                        "rejected": "🔴"
                    }.get(prop["status"], "⚪")

                    type_emoji = {
                        "update_existing_page": "📝",
                        "create_new_page": "➕",
                        "create_new_category": "📁",
                        "no_action": "⏸️"
                    }.get(prop["proposal_type"], "📄")

                    with st.expander(
                        f"{status_emoji} {type_emoji} {prop['target_title']}",
                        expanded=False
                    ):
                        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
                        col1.markdown(f"**ID:** {prop['id']}")
                        col2.markdown(f"**Τύπος:** `{prop['proposal_type']}`")
                        col3.markdown(f"**Status:** `{prop['status']}`")

                        # Preview button
                        if col4.button("🔍 Preview", key=f"preview_{prop['id']}", use_container_width=True):
                            st.session_state.preview_proposal_id = prop['id']
                            st.rerun()

                        if col5.button("✅ Approve", key=f"approve_{prop['id']}", use_container_width=True):
                            update_proposal_status(api_url, prop["id"], "approved")

                        if col6.button("❌ Reject", key=f"reject_{prop['id']}", use_container_width=True):
                            update_proposal_status(api_url, prop["id"], "rejected")

                        st.markdown(f"**Περίληψη:** {prop['summary']}")

                        if prop.get('parent_pillar'):
                            st.markdown(f"**Parent Pillar:** `{prop['parent_pillar']}`")

                        if prop.get('priority'):
                            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(prop['priority'], "⚪")
                            st.markdown(f"**Priority:** {priority_color} `{prop['priority']}`")

                        if prop.get('outline'):
                            st.markdown("**Outline:**")
                            st.text(prop['outline'])

                        if prop.get('suggested_schema'):
                            st.markdown(f"**Schema:** `{prop['suggested_schema']}`")

                        if prop.get('faq_suggestions'):
                            st.markdown("**FAQ Suggestions:** Υπάρχουν")

                        st.caption(f"Δημιουργήθηκε: {prop.get('created_at', 'N/A')}")
            else:
                st.info("Δεν υπάρχουν proposals ακόμα. Τρέξε μια ανάλυση!")
        else:
            st.error(f"Σφάλμα: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Δεν μπορώ να συνδεθώ στο API")
    except Exception as e:
        st.error(f"Σφάλμα: {str(e)}")

# Tab 3: Preview Comparison
with tab3:
    st.header("🔍 Preview - Σύγκριση Υπάρχοντος vs Προτεινόμενου")

    preview_proposals = []
    preview_proposals_error = None
    try:
        proposals_response = requests.get(f"{api_url}/proposals", timeout=10)
        if proposals_response.status_code == 200:
            preview_proposals = proposals_response.json()
        else:
            preview_proposals_error = f"{proposals_response.status_code} - {proposals_response.text}"
    except requests.exceptions.ConnectionError:
        preview_proposals_error = "Δεν μπορώ να συνδεθώ στο API"
    except Exception as e:
        preview_proposals_error = str(e)

    # Proposal selector or manual fallback
    col1, col2, col3 = st.columns([2, 1, 1])
    proposal_ids = []
    with col1:
        if preview_proposals:
            proposal_labels = {
                f"#{prop['id']} - {prop['target_title']} ({prop['proposal_type']}, {prop['status']})": prop
                for prop in preview_proposals
            }
            proposal_ids = [prop["id"] for prop in preview_proposals]
            selected_index = 0
            if st.session_state.preview_proposal_id in proposal_ids:
                selected_index = proposal_ids.index(st.session_state.preview_proposal_id)

            selected_label = st.selectbox(
                "Πρόταση",
                options=list(proposal_labels.keys()),
                index=selected_index,
                help="Επέλεξε proposal με βάση τον τίτλο αντί να ψάχνεις το ID",
            )
            selected_proposal = proposal_labels[selected_label]
            preview_id = selected_proposal["id"]
            st.caption(
                f"ID: `{preview_id}` | Τύπος: `{selected_proposal['proposal_type']}` | "
                f"Status: `{selected_proposal['status']}`"
            )
        else:
            if preview_proposals_error:
                st.warning(f"Δεν φορτώθηκαν proposals: {preview_proposals_error}")
            preview_id = st.number_input(
                "Proposal ID",
                min_value=1,
                value=st.session_state.preview_proposal_id or 1,
                step=1,
                help="Fallback χειροκίνητης επιλογής όταν δεν φορτώνει η λίστα proposals",
            )
    with col2:
        generate_btn = st.button("🚀 Preview", type="primary", use_container_width=True)
    with col3:
        generate_html_btn = st.button("📄 Δημιουργία HTML", type="secondary", use_container_width=True)

    # Custom instructions for HTML generation
    custom_instructions = st.text_area(
        "📝 Συμπληρωματικές Οδηγίες (προαιρετικό)",
        placeholder="π.χ. Δώσε έμφαση στην ασφάλεια, πρόσθεσε περισσότερα παραδείγματα, χρησιμοποίησε πιο τεχνική γλώσσα, ανέφερε τιμές...",
        help="Οδηγίες που θα δοθούν στο AI για να προσαρμόσει το περιεχόμενο",
        height=80,
        key="custom_instructions"
    )

    if generate_btn or st.session_state.preview_proposal_id:
        proposal_id = preview_id if generate_btn else st.session_state.preview_proposal_id
        if preview_proposals and proposal_id not in proposal_ids:
            proposal_id = preview_id
        st.session_state.preview_proposal_id = None  # Reset

        with st.spinner("Δημιουργία preview... (χρησιμοποιεί AI για τις προτάσεις)"):
            try:
                response = requests.get(
                    f"{api_url}/proposals/{proposal_id}/preview",
                    timeout=120
                )

                if response.status_code == 200:
                    data = response.json()
                    preview = data.get("preview", {})
                    changes = preview.get("changes", {})

                    st.success(f"✅ Preview για: **{data.get('target_title')}**")
                    st.caption(f"Τύπος: `{data.get('proposal_type')}`")

                    # Summary
                    if changes.get("summary"):
                        st.info(f"📝 **Σύνοψη αλλαγών:** {changes.get('summary')}")

                    # Meta Title comparison
                    if changes.get("meta_title"):
                        st.subheader("📌 Meta Title")
                        meta_title = changes["meta_title"]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Υπάρχον:**")
                            current_title = meta_title.get("current") or "—"
                            st.code(current_title, language=None)
                            st.caption(f"Χαρακτήρες: {len(current_title)}")
                        with col2:
                            st.markdown("**Προτεινόμενο:**")
                            proposed_title = meta_title.get("proposed") or "—"
                            st.code(proposed_title, language=None)
                            st.caption(f"Χαρακτήρες: {len(proposed_title)}")
                        if meta_title.get("change_reason"):
                            st.caption(f"💡 {meta_title['change_reason']}")

                    # Meta Description comparison
                    if changes.get("meta_description"):
                        st.subheader("📝 Meta Description")
                        meta_desc = changes["meta_description"]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Υπάρχον:**")
                            current_desc = meta_desc.get("current") or "—"
                            st.text_area("", value=current_desc, height=100, disabled=True, key="current_desc")
                            st.caption(f"Χαρακτήρες: {len(current_desc)}")
                        with col2:
                            st.markdown("**Προτεινόμενο:**")
                            proposed_desc = meta_desc.get("proposed") or "—"
                            st.text_area("", value=proposed_desc, height=100, disabled=True, key="proposed_desc")
                            st.caption(f"Χαρακτήρες: {len(proposed_desc)}")
                        if meta_desc.get("change_reason"):
                            st.caption(f"💡 {meta_desc['change_reason']}")

                    # Focus Keyphrase
                    if changes.get("focus_keyphrase"):
                        st.subheader("🔑 Focus Keyphrase")
                        keyphrase = changes["focus_keyphrase"]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Υπάρχον:**")
                            st.code(keyphrase.get("current", "—") or "Δεν έχει οριστεί", language=None)
                        with col2:
                            st.markdown("**Προτεινόμενο:**")
                            st.code(keyphrase.get("proposed", "—"), language=None)
                        if keyphrase.get("change_reason"):
                            st.caption(f"💡 {keyphrase['change_reason']}")

                    # Content Changes
                    if changes.get("content_changes"):
                        st.subheader("📄 Αλλαγές Περιεχομένου")
                        for i, change in enumerate(changes["content_changes"], 1):
                            with st.expander(f"{i}. {change.get('section', 'Section')} ({change.get('change_type', 'modify')})"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown("**Υπάρχον:**")
                                    current = change.get("current") or "—"
                                    st.text_area("", value=current, height=150, disabled=True, key=f"content_current_{i}")
                                with col2:
                                    st.markdown("**Προτεινόμενο:**")
                                    proposed = change.get("proposed", "—")
                                    st.text_area("", value=proposed, height=150, disabled=True, key=f"content_proposed_{i}")
                                if change.get("change_reason"):
                                    st.caption(f"💡 {change['change_reason']}")

                    # FAQ Section
                    if changes.get("faq_section"):
                        st.subheader("❓ Προτεινόμενο FAQ Section")
                        st.markdown("*Προσθήκη αυτών των FAQs με FAQPage schema:*")
                        for i, faq in enumerate(changes["faq_section"], 1):
                            st.markdown(f"**Q{i}: {faq.get('question', '')}**")
                            st.markdown(f"A: {faq.get('answer', '')}")
                            st.divider()

                    # Schema additions
                    if changes.get("schema_additions"):
                        st.subheader("🏗️ Προτεινόμενα Schemas")
                        schemas = changes["schema_additions"]
                        if isinstance(schemas, list):
                            for schema in schemas:
                                st.markdown(f"- `{schema}`")
                        else:
                            st.markdown(f"- `{schemas}`")

                    # Current page info
                    current_page = preview.get("current_page", {})
                    if current_page and current_page.get("url"):
                        st.divider()
                        st.markdown(f"🔗 **Σελίδα:** [{current_page.get('title', 'Link')}]({current_page.get('url')})")

                elif response.status_code == 404:
                    st.error("❌ Δεν βρέθηκε το proposal")
                else:
                    st.error(f"❌ Σφάλμα: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                st.error("❌ Timeout - η δημιουργία preview πήρε πολύ χρόνο")
            except requests.exceptions.ConnectionError:
                st.error("❌ Δεν μπορώ να συνδεθώ στο API")
            except Exception as e:
                st.error(f"❌ Σφάλμα: {str(e)}")

    # Generate Full HTML Content
    if generate_html_btn:
        with st.spinner("Δημιουργία πλήρους HTML περιεχομένου... (μπορεί να πάρει 30-60 δευτερόλεπτα)"):
            try:
                # Prepare request with optional custom instructions
                request_body = {}
                if custom_instructions and custom_instructions.strip():
                    request_body["custom_instructions"] = custom_instructions.strip()

                response = requests.post(
                    f"{api_url}/proposals/{preview_id}/generate-html",
                    json=request_body if request_body else None,
                    timeout=180
                )

                if response.status_code == 200:
                    data = response.json()
                    result = data.get("result", {})
                    st.session_state.generated_html_result = result

                elif response.status_code == 404:
                    st.error("❌ Δεν βρέθηκε το proposal")
                else:
                    st.error(f"❌ Σφάλμα: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                st.error("❌ Timeout - η δημιουργία HTML πήρε πολύ χρόνο")
            except requests.exceptions.ConnectionError:
                st.error("❌ Δεν μπορώ να συνδεθώ στο API")
            except Exception as e:
                st.error(f"❌ Σφάλμα: {str(e)}")

    # Display Generated HTML Result
    if st.session_state.generated_html_result:
        result = st.session_state.generated_html_result
        st.divider()
        st.subheader("📄 Παραγόμενο HTML Περιεχόμενο")

        # Metadata
        st.success(f"✅ Δημιουργήθηκε: **{result.get('target_title')}**")

        # SEO Score Display
        seo_score = result.get("seo_score", {})
        if seo_score:
            score = seo_score.get("total_score", 0)
            grade = seo_score.get("grade", "?")

            # Color based on grade
            grade_colors = {"A": "🟢", "B": "🟢", "C": "🟡", "D": "🟠", "F": "🔴"}
            grade_emoji = grade_colors.get(grade, "⚪")

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("SEO Score", f"{score}/100")
            col2.metric("Grade", f"{grade_emoji} {grade}")
            col3.metric("Λέξεις", result.get("word_count", 0))
            col4.metric("Keywords", result.get("keyword_count", 0))
            col5.metric("Links", len(result.get("internal_links", [])))

            # SEO Score Details
            with st.expander(f"📊 SEO Analysis - {seo_score.get('summary', '')}", expanded=True):
                checks = seo_score.get("checks", [])

                # Group by importance
                critical = [c for c in checks if c.get("importance") == "critical"]
                important = [c for c in checks if c.get("importance") == "important"]
                nice_to_have = [c for c in checks if c.get("importance") == "nice_to_have"]

                if critical:
                    st.markdown("**🔴 Κρίσιμα:**")
                    for check in critical:
                        icon = "✅" if check.get("passed") else "❌"
                        st.markdown(f"- {icon} **{check.get('name')}**: {check.get('message')}")

                if important:
                    st.markdown("**🟡 Σημαντικά:**")
                    for check in important:
                        icon = "✅" if check.get("passed") else "❌"
                        st.markdown(f"- {icon} **{check.get('name')}**: {check.get('message')}")

                if nice_to_have:
                    st.markdown("**🟢 Προαιρετικά:**")
                    for check in nice_to_have:
                        icon = "✅" if check.get("passed") else "⚪"
                        st.markdown(f"- {icon} **{check.get('name')}**: {check.get('message')}")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Λέξεις", result.get("word_count", 0))
            col2.metric("Sections", len(result.get("sections", [])))
            col3.metric("FAQ", "Ναι" if result.get("includes_faq") else "Όχι")
            col4.metric("Proposal ID", result.get("proposal_id", ""))

        # SEO Meta
        with st.expander("🔍 SEO Metadata", expanded=False):
            st.markdown(f"**Meta Title:** `{result.get('meta_title', '')}`")
            st.caption(f"Χαρακτήρες: {len(result.get('meta_title', ''))}")
            st.markdown(f"**Meta Description:** {result.get('meta_description', '')}")
            st.caption(f"Χαρακτήρες: {len(result.get('meta_description', ''))}")
            st.markdown(f"**Focus Keyphrase:** `{result.get('focus_keyphrase', '')}`")

        # Sections
        if result.get("sections"):
            with st.expander("📑 Sections του κειμένου"):
                for i, section in enumerate(result.get("sections", []), 1):
                    st.markdown(f"{i}. {section}")

        # HTML Content - Copyable
        st.subheader("📋 HTML για Copy-Paste στο Elementor")
        html_content = result.get("html_content", "")

        st.code(html_content, language="html")

        # Download button
        st.download_button(
            label="⬇️ Κατέβασε HTML αρχείο",
            data=html_content,
            file_name=f"content_{result.get('proposal_id', 0)}.html",
            mime="text/html",
            use_container_width=True
        )

        # File path info
        if result.get("file_path"):
            st.info(f"📁 Αποθηκεύτηκε: `{result.get('file_path')}`")

        # Current page link if exists
        if result.get("current_page_url"):
            st.markdown(f"🔗 **Υπάρχουσα σελίδα:** [{result.get('current_page_url')}]({result.get('current_page_url')})")

        # Clear button
        if st.button("🗑️ Καθαρισμός", use_container_width=True):
            st.session_state.generated_html_result = None
            st.rerun()

# Tab 4: Site Audit
with tab4:
    st.header("Site Audit")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        audit_include_pages = st.checkbox("Εμφάνιση λίστας σελίδων", value=False)
    with col2:
        run_audit_btn = st.button("📊 Εκτέλεση Audit", type="primary", use_container_width=True)
    with col3:
        clear_cache_btn = st.button("♻️ Καθαρισμός προσωρινής μνήμης", use_container_width=True)

    if clear_cache_btn:
        try:
            response = requests.post(
                f"{api_url}/site/cache/clear",
                params={"site_url": site_url},
                timeout=10,
            )
            if response.status_code == 200:
                st.success("Η προσωρινή μνήμη καθαρίστηκε")
            else:
                st.error(f"Σφάλμα καθαρισμού προσωρινής μνήμης: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Δεν μπορώ να συνδεθώ στο API")
        except Exception as e:
            st.error(f"Σφάλμα καθαρισμού προσωρινής μνήμης: {str(e)}")

    if run_audit_btn:
        with st.spinner("Γίνεται γρήγορος έλεγχος του site..."):
            try:
                response = requests.get(
                    f"{api_url}/site/audit",
                    params={"site_url": site_url, "include_pages": audit_include_pages},
                    timeout=120,
                )

                if response.status_code == 200:
                    audit = response.json()
                    st.success(f"Audit ολοκληρώθηκε για {audit.get('site_url')}")

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Σελίδες", audit.get("site_pages_found", 0))
                    col2.metric("Pillars", audit.get("topology", {}).get("pillars_count", 0))
                    col3.metric("Yoast Issues", audit.get("yoast", {}).get("total_issues", 0))
                    col4.metric("AI Readiness", f"{audit.get('schema', {}).get('ai_readiness_score', 0)}%")

                    with st.expander("Topology", expanded=True):
                        topology = audit.get("topology", {})
                        st.write({
                            "homepage": topology.get("homepage"),
                            "satellites_count": topology.get("satellites_count"),
                            "orphans_count": topology.get("orphans_count"),
                        })
                        orphan_pages = topology.get("orphan_pages", [])
                        if orphan_pages:
                            st.markdown("**Orphan pages:**")
                            for page in orphan_pages:
                                st.markdown(f"- `{page.get('slug')}` - {page.get('title')}")

                    with st.expander("Homepage", expanded=True):
                        homepage = audit.get("homepage", {})
                        if homepage.get("found"):
                            metrics = homepage.get("metrics", {})
                            col1, col2, col3, col4, col5 = st.columns(5)
                            col1.metric("Score", f"{homepage.get('score', 0)}/100")
                            col2.metric("Λέξεις", metrics.get("word_count", 0))
                            col3.metric("Internal Links", metrics.get("internal_links_count", 0))
                            col4.metric("Pillar Links", metrics.get("linked_pillars_count", 0))
                            col5.metric("CTA", "Ναι" if metrics.get("has_cta") else "Όχι")

                            st.caption(
                                f"Ύφος προσφώνησης: `{metrics.get('detected_addressing', 'unknown')}`"
                            )

                            issues = homepage.get("issues", [])
                            if issues:
                                st.markdown("**Θέματα:**")
                                for issue in issues:
                                    st.markdown(
                                        f"- **{issue.get('severity', 'n/a')}** "
                                        f"`{issue.get('type', 'issue')}`: {issue.get('message', '')}"
                                    )

                            recommendations = homepage.get("recommendations", [])
                            if recommendations:
                                st.markdown("**Προτάσεις διαχείρισης αρχικής:**")
                                for recommendation in recommendations:
                                    st.markdown(f"- {recommendation}")

                            linked_pillars = homepage.get("linked_pillars", [])
                            if linked_pillars:
                                st.markdown("**Pillars που συνδέονται από την αρχική:**")
                                for pillar in linked_pillars:
                                    st.markdown(f"- `{pillar.get('slug')}` - {pillar.get('title')}")
                        else:
                            st.warning("Δεν εντοπίστηκε αρχική σελίδα στο audit.")
                            for recommendation in homepage.get("recommendations", []):
                                st.markdown(f"- {recommendation}")

                    with st.expander("Yoast Priorities", expanded=True):
                        priorities = audit.get("yoast", {}).get("priority_pages", [])
                        if priorities:
                            for item in priorities:
                                st.markdown(f"- `{item.get('slug')}`: {item.get('issues_count', 0)} issues")
                        else:
                            st.info("Δεν βρέθηκαν Yoast priorities.")

                    with st.expander("Schema Suggestions", expanded=True):
                        schema = audit.get("schema", {})
                        st.write({
                            "coverage_percent": schema.get("schema_coverage_percent"),
                            "types_found": schema.get("schema_types_found"),
                        })
                        for suggestion in schema.get("improvement_suggestions", []):
                            st.markdown(
                                f"- **{suggestion.get('priority', 'n/a')}** "
                                f"`{suggestion.get('schema', suggestion.get('type', 'schema'))}`: "
                                f"{suggestion.get('reason', '')}"
                            )

                    if audit_include_pages and audit.get("pages"):
                        with st.expander("Pages", expanded=False):
                            st.dataframe(audit.get("pages"), use_container_width=True)
                else:
                    st.error(f"Σφάλμα audit: {response.status_code} - {response.text}")
            except requests.exceptions.Timeout:
                st.error("Timeout - το audit πήρε πολύ χρόνο")
            except requests.exceptions.ConnectionError:
                st.error("Δεν μπορώ να συνδεθώ στο API")
            except Exception as e:
                st.error(f"Σφάλμα audit: {str(e)}")

# Tab 5: Homepage Guidance
with tab5:
    st.header("Οδηγίες Διόρθωσης Αρχικής Σελίδας")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.caption(f"Site: {site_url}")
    with col2:
        run_homepage_guidance_btn = st.button(
            "🏠 Δημιουργία οδηγιών αρχικής",
            type="primary",
            use_container_width=True,
        )

    if run_homepage_guidance_btn:
        with st.spinner("Ανάλυση αρχικής σελίδας και συνολικής αρχιτεκτονικής..."):
            try:
                response = requests.get(
                    f"{api_url}/site/homepage-guidance",
                    params={"site_url": site_url},
                    timeout=120,
                )

                if response.status_code == 200:
                    data = response.json()
                    guidance = data.get("guidance", {})
                    homepage_analysis = guidance.get("homepage_analysis", {})

                    st.success(f"Οδηγίες έτοιμες για {data.get('site_url')}")

                    if homepage_analysis.get("found"):
                        metrics = homepage_analysis.get("metrics", {})
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("Homepage Score", f"{homepage_analysis.get('score', 0)}/100")
                        col2.metric("Λέξεις", metrics.get("word_count", 0))
                        col3.metric("Internal Links", metrics.get("internal_links_count", 0))
                        col4.metric("Pillar Links", metrics.get("linked_pillars_count", 0))
                        col5.metric("CTA", "Ναι" if metrics.get("has_cta") else "Όχι")
                    else:
                        st.warning("Δεν εντοπίστηκε αρχική σελίδα στο WordPress content.")

                    architecture = guidance.get("architecture", {})
                    st.subheader("Αρχιτεκτονική Δομή")
                    st.markdown(f"**Ρόλος αρχικής:** {architecture.get('role', '')}")
                    st.markdown(f"**Στόχος μήκους:** {architecture.get('target_length', '')}")

                    for section in architecture.get("recommended_sections", []):
                        with st.expander(f"{section.get('order')}. {section.get('name')}", expanded=False):
                            st.markdown(f"**Σκοπός:** {section.get('purpose', '')}")
                            st.markdown(f"**Οδηγία περιεχομένου:** {section.get('content_instruction', '')}")

                    semantic = guidance.get("semantic", {})
                    st.subheader("Νοηματική Διόρθωση")
                    st.markdown(f"**Κεντρικό μήνυμα:** {semantic.get('core_message', '')}")
                    tone = semantic.get("tone", {})
                    st.markdown(f"**Ύφος/προσφώνηση:** `{tone.get('addressing', 'unknown')}`")
                    st.caption(tone.get("instruction", ""))

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Κανόνες νοήματος:**")
                        for rule in semantic.get("meaning_rules", []):
                            st.markdown(f"- {rule}")
                    with col2:
                        st.markdown("**Να αποφευχθούν:**")
                        for item in semantic.get("avoid", []):
                            st.markdown(f"- {item}")

                    link_plan = guidance.get("internal_link_plan", {})
                    st.subheader("Πλάνο Internal Links")
                    st.markdown(link_plan.get("target", ""))
                    st.caption(link_plan.get("anchor_text_rule", ""))

                    missing_links = link_plan.get("missing_priority_links", [])
                    if missing_links:
                        st.markdown("**Προτεραιότητα για links από την αρχική:**")
                        for link in missing_links:
                            st.markdown(f"- `{link.get('slug')}` - {link.get('title')}")

                    allocation = guidance.get("content_allocation", {})
                    st.subheader("Κατανομή Περιεχομένου")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**Μένει στην αρχική:**")
                        for item in allocation.get("keep_on_homepage", []):
                            st.markdown(f"- {item}")
                    with col2:
                        st.markdown("**Μεταφέρεται σε pillars:**")
                        move_items = allocation.get("move_to_pillar_pages", [])
                        if move_items:
                            for item in move_items:
                                st.markdown(f"- {item}")
                        else:
                            st.caption("Δεν απαιτείται μεταφορά βάσει μήκους.")
                    with col3:
                        st.markdown("**Υποστήριξη από satellites/orphans:**")
                        support_items = allocation.get("support_with_satellites", []) + allocation.get("review_orphans_for_linking", [])
                        if support_items:
                            for item in support_items[:8]:
                                st.markdown(f"- {item}")
                        else:
                            st.caption("Δεν βρέθηκαν σχετικά items.")

                    st.subheader("Action Plan")
                    for action in guidance.get("action_plan", []):
                        with st.expander(f"{action.get('priority', 'n/a').upper()} - {action.get('area', '')}", expanded=True):
                            st.markdown(f"**Τι κάνουμε:** {action.get('instruction', '')}")
                            st.markdown(f"**Γιατί:** {action.get('reason', '')}")
                else:
                    st.error(f"Σφάλμα οδηγιών αρχικής: {response.status_code} - {response.text}")
            except requests.exceptions.Timeout:
                st.error("Timeout - η ανάλυση αρχικής πήρε πολύ χρόνο")
            except requests.exceptions.ConnectionError:
                st.error("Δεν μπορώ να συνδεθώ στο API")
            except Exception as e:
                st.error(f"Σφάλμα οδηγιών αρχικής: {str(e)}")

# Footer
st.divider()
st.caption("SEO Agent MVP v0.2 | Powered by FastAPI + LangGraph + Gemini | Style + Topology + Yoast + Schema + GEO")
