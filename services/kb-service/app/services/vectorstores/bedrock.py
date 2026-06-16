"""Amazon Bedrock Knowledge Bases (managed RAG).

Bedrock KB embeds + indexes server-side, so this store ingests the document *text*
to the KB's S3 data source and retrieves via the Agent Runtime ``retrieve`` API
(the local embedding vector is unused for this stack). Requires a pre-provisioned
Knowledge Base + S3 data source; degrades to the in-process index otherwise.
"""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class BedrockKbStore(VectorStore):
    stack = "bedrock"

    def ready(self) -> bool:
        return bool(settings.bedrock_kb_id and settings.bedrock_kb_s3_bucket)

    def _s3(self):
        import boto3

        return boto3.client("s3", region_name=settings.aws_region)

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if not self.ready():
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            key = f"{settings.bedrock_kb_prefix}{namespace}/{doc_id}.txt"
            self._s3().put_object(
                Bucket=settings.bedrock_kb_s3_bucket, Key=key,
                Body=(text or "").encode("utf-8"), ContentType="text/plain",
            )
            # Kick a data-source sync so the new doc is indexed (best-effort).
            if settings.bedrock_kb_data_source_id:
                import boto3

                boto3.client("bedrock-agent", region_name=settings.aws_region).start_ingestion_job(
                    knowledgeBaseId=settings.bedrock_kb_id,
                    dataSourceId=settings.bedrock_kb_data_source_id,
                )
        except Exception as exc:
            log.warning("bedrock-kb upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if not self.ready():
            return self._mem_query(namespace, vector, top_k)
        try:
            import boto3

            rt = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)
            resp = rt.retrieve(
                knowledgeBaseId=settings.bedrock_kb_id,
                retrievalQuery={"text": text or ""},
                retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": top_k}},
            )
            out = []
            for r in resp.get("retrievalResults", []):
                uri = (r.get("location", {}).get("s3Location", {}) or {}).get("uri", "")
                doc_id = uri.rsplit("/", 1)[-1].removesuffix(".txt") if uri else ""
                snippet = (r.get("content", {}) or {}).get("text", "")
                out.append(
                    {"id": doc_id, "score": float(r.get("score", 0.0)),
                     "payload": {"generation_id": doc_id, "title": snippet[:200]}}
                )
            return out
        except Exception as exc:
            log.warning("bedrock-kb retrieve failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)

    def delete_namespace(self, *, namespace, db=None):
        self._mem_delete(namespace)
        if not self.ready():
            return
        try:
            # Remove the KB's docs from the S3 data source, then re-sync the KB so
            # the deletions propagate to the managed index (best-effort).
            s3 = self._s3()
            prefix = f"{settings.bedrock_kb_prefix}{namespace}/"
            listed = s3.list_objects_v2(Bucket=settings.bedrock_kb_s3_bucket, Prefix=prefix)
            keys = [{"Key": o["Key"]} for o in listed.get("Contents", [])]
            if keys:
                s3.delete_objects(Bucket=settings.bedrock_kb_s3_bucket, Delete={"Objects": keys})
            if settings.bedrock_kb_data_source_id:
                import boto3

                boto3.client("bedrock-agent", region_name=settings.aws_region).start_ingestion_job(
                    knowledgeBaseId=settings.bedrock_kb_id,
                    dataSourceId=settings.bedrock_kb_data_source_id,
                )
        except Exception as exc:
            log.warning("bedrock-kb delete_namespace failed: %s", exc)
