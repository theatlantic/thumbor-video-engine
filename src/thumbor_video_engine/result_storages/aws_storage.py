from datetime import datetime, timezone
from deprecated import deprecated
from hashlib import sha1
from urllib.parse import unquote
from os.path import join

from thumbor.config import Config
from thumbor.engines import BaseEngine
from thumbor.result_storages import ResultStorageResult
from thumbor.utils import logger
import thumbor_aws.result_storage
from thumbor_aws.utils import normalize_path
from .base import BaseStorage

Config.define(
    "TC_AWS_RANDOMIZE_KEYS", False, "Randomize S3 bucket keys", "tc_aws Compatibility"
)
Config.define(
    "TC_AWS_ROOT_IMAGE_NAME",
    "",
    "When resizing a URL that ends in a slash, what should the corresponding cache key be?",
    "tc_aws Compatibility",
)


class Storage(BaseStorage, thumbor_aws.result_storage.Storage):
    @property
    def prefix(self):
        auto_component = self.get_auto_path_component()
        if auto_component:
            return f"{self.root_path}/{auto_component}".lstrip("/")
        else:
            return self.root_path.lstrip("/")

    def normalize_path(self, path):
        if not self.context.config.THUMBOR_AWS_RUN_IN_COMPATIBILITY_MODE:
            return normalize_path(self.prefix, path)

        segments = [path.lstrip("/")]

        root_path = self.context.config.TC_AWS_RESULT_STORAGE_ROOT_PATH

        if root_path:
            segments.insert(0, root_path.lstrip("/"))

        auto_component = self.get_auto_path_component()
        if auto_component:
            segments.append(auto_component)

        if self.context.config.TC_AWS_RANDOMIZE_KEYS:
            segments.insert(0, self._generate_digest(segments))

        normalized_path = join(*segments)
        if normalized_path.endswith("/"):
            normalized_path += self.context.config.TC_AWS_ROOT_IMAGE_NAME

        return unquote(normalized_path)

    def _generate_digest(self, segments):
        return sha1(".".join(segments).encode("utf-8")).hexdigest()

    async def put(self, image_bytes: bytes) -> str:
        file_abspath = self.normalize_path(self.context.request.url)
        logger.debug("[RESULT_STORAGE] putting at %s", file_abspath)
        content_type = BaseEngine.get_mimetype(image_bytes)
        response = await self.upload(
            file_abspath,
            image_bytes,
            content_type,
            self.context.config.AWS_DEFAULT_LOCATION,
        )
        logger.info("[RESULT_STORAGE] Image uploaded successfully to %s", file_abspath)
        return response

    async def get(self) -> ResultStorageResult:
        path = self.context.request.url
        file_abspath = self.normalize_path(path)

        logger.debug("[RESULT_STORAGE] getting from %s", file_abspath)

        exists = await self.object_exists(file_abspath)
        if not exists:
            logger.debug("[RESULT_STORAGE] image not found at %s", file_abspath)
            return None

        status, body, last_modified = await self.get_data(
            self.bucket_name, file_abspath
        )

        if status != 200 or self._is_expired(last_modified):
            logger.debug(
                "[RESULT_STORAGE] cached image has expired (status %s)", status
            )
            return None

        logger.info(
            "[RESULT_STORAGE] Image retrieved successfully at %s.",
            file_abspath,
        )

        return ResultStorageResult(
            buffer=body,
            metadata={
                "LastModified": last_modified.replace(tzinfo=timezone.utc),
                "ContentLength": len(body),
                "ContentType": BaseEngine.get_mimetype(body),
            },
        )

    @deprecated(version="7.0.0", reason="Use result's last_modified instead")
    async def last_updated(  # pylint: disable=invalid-overridden-method
        self,
    ) -> datetime:
        path = self.context.request.url
        file_abspath = self.normalize_path(path)
        logger.debug("[RESULT_STORAGE] getting from %s", file_abspath)

        response = await self.get_object_metadata(file_abspath)
        return datetime.strptime(
            response["ResponseMetadata"]["HTTPHeaders"]["last-modified"],
            "%a, %d %b %Y %H:%M:%S %Z",
        )
