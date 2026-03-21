from app.models.asset import Asset
from app.models.project import Project
from app.models.render_job import RenderJob
from app.models.scene import Scene
from app.models.scene_version import SceneVersion
from app.schemas.asset import AssetResponse
from app.schemas.job import JobResponse
from app.schemas.project import ProjectDetailResponse, ProjectResponse
from app.schemas.scene import SceneResponse, SceneVersionResponse


def to_asset_response(asset: Asset) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        mime_type=asset.mime_type,
        storage_path=asset.storage_path,
        duration_ms=asset.duration_ms,
        checksum_sha256=asset.checksum_sha256,
    )


def to_scene_version_response(version: SceneVersion) -> SceneVersionResponse:
    return SceneVersionResponse(
        id=version.id,
        scene_id=version.scene_id,
        version_no=version.version_no,
        prompt=version.prompt,
        manim_code=version.manim_code,
        validation_status=version.validation_status,
        error_log=version.error_log,
        style_preset=version.style_preset,
        max_duration_sec=version.max_duration_sec,
        aspect_ratio=version.aspect_ratio,
        created_at=version.created_at,
    )


def to_scene_response(scene: Scene) -> SceneResponse:
    versions = sorted(scene.versions, key=lambda item: item.version_no)
    sorted_assets = sorted(scene.assets, key=lambda a: a.created_at, reverse=True)
    thumbnail = next(
        (a for a in sorted_assets if a.asset_type == "thumbnail"),
        None,
    )
    video_preview = next(
        (a for a in sorted_assets if a.asset_type in ("video_preview", "video_hd")),
        None,
    )
    return SceneResponse(
        id=scene.id,
        title=scene.title,
        order_index=scene.order_index,
        created_at=scene.created_at,
        versions=[to_scene_version_response(v) for v in versions],
        thumbnail_path=thumbnail.storage_path if thumbnail else None,
        video_preview_path=video_preview.storage_path if video_preview else None,
    )


def to_project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        created_at=project.created_at,
    )


def to_project_detail_response(project: Project) -> ProjectDetailResponse:
    scenes = sorted(project.scenes, key=lambda item: item.order_index)
    return ProjectDetailResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        created_at=project.created_at,
        scenes=[to_scene_response(s) for s in scenes],
    )


def to_job_response(job: RenderJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        attempt=job.attempt,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_message=job.error_message,
        metrics=job.metrics or {},
        assets=[to_asset_response(asset) for asset in job.assets],
    )

