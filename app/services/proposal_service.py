import logging

from sqlalchemy.orm import Session

from app.models import ContentProposal

logger = logging.getLogger(__name__)


class ProposalService:
    def persist_proposals(
        self,
        db: Session,
        workflow_run_id: int,
        proposals: list[dict],
    ) -> list[ContentProposal]:
        saved: list[ContentProposal] = []

        for item in proposals:
            outline = item.get("outline", [])
            if isinstance(outline, list):
                outline = "\n".join(outline)

            schema = item.get("suggested_schema", [])
            if isinstance(schema, list):
                schema = ", ".join(schema)

            # Handle FAQ suggestions
            faq_suggestions = item.get("faq_suggestions", [])
            if isinstance(faq_suggestions, list):
                import json
                faq_suggestions = json.dumps(faq_suggestions, ensure_ascii=False)

            # Handle schema additions
            schema_additions = item.get("schema_additions", [])
            if isinstance(schema_additions, list):
                schema_additions = ", ".join(schema_additions)

            # Handle SEO meta suggestions
            seo_meta = item.get("seo_meta_suggestions", {})
            if isinstance(seo_meta, dict):
                import json
                seo_meta = json.dumps(seo_meta, ensure_ascii=False)

            proposal = ContentProposal(
                workflow_run_id=workflow_run_id,
                proposal_type=item.get("proposal_type", "no_action"),
                target_title=item.get("target_title", "Χωρίς τίτλο"),
                parent_pillar=item.get("parent_pillar"),
                summary=item.get("summary", ""),
                outline=str(outline),
                suggested_schema=str(schema),
                faq_suggestions=str(faq_suggestions) if faq_suggestions else None,
                schema_additions=str(schema_additions) if schema_additions else None,
                seo_meta_suggestions=str(seo_meta) if seo_meta else None,
                priority=item.get("priority", "medium"),
                status="needs_review",
            )
            db.add(proposal)
            saved.append(proposal)

        db.commit()

        for proposal in saved:
            db.refresh(proposal)

        logger.info("Persisted %d proposals for workflow_run_id=%d", len(saved), workflow_run_id)
        return saved
