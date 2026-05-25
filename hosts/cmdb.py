import logging

from blueking.component.shortcuts import get_client_by_request

logger = logging.getLogger(__name__)

DEMO_BUSINESS_MARKERS = ("demo", "\u4f53\u9a8c")
HIDDEN_SET_MARKERS = ("\u6d4b\u8bd5", "test set", "test cluster", "testing")
HOST_DETAIL_FIELD_ALLOWLIST = {
    "bk_host_id",
    "bk_host_innerip",
    "bk_host_outerip",
    "bk_host_name",
    "bk_os_name",
    "bk_os_type",
    "bk_cloud_id",
    "bk_cloud_inst_id",
    "bk_cpu",
    "bk_mem",
    "bk_disk",
    "operator",
    "bk_bak_operator",
    "bk_asset_id",
    "bk_sn",
    "bk_comment",
}
EMPTY_DETAIL_VALUES = {"", "-", "\u65e0", "none", "null"}


class CmdbServiceError(Exception):
    pass


class CmdbService:
    def __init__(self, request):
        self.client = get_client_by_request(request)

    def list_businesses(self):
        params = {
            "fields": ["bk_biz_id", "bk_biz_name"],
            "page": {"start": 0, "limit": 200, "sort": ""},
        }
        rows = self._call(self.client.cc.search_business, params)
        return [row for row in rows if not self._is_demo_business(row)]

    def list_sets(self, bk_biz_id):
        params = {
            "bk_biz_id": bk_biz_id,
            "fields": ["bk_set_id", "bk_set_name", "bk_biz_id"],
            "condition": {"bk_biz_id": bk_biz_id},
            "page": {"start": 0, "limit": 200, "sort": ""},
        }
        rows = self._call(self.client.cc.search_set, params)
        rows = [row for row in rows if not self._is_hidden_set(row)]
        return self._merge_same_name_rows(rows, "bk_set_id", "bk_set_name", "bk_set_ids")

    def list_modules(self, bk_biz_id, bk_set_ids):
        rows = []
        for bk_set_id in bk_set_ids:
            params = {
                "bk_biz_id": bk_biz_id,
                "fields": ["bk_module_id", "bk_module_name", "bk_set_id", "bk_biz_id"],
                "condition": {"bk_biz_id": bk_biz_id, "bk_set_id": bk_set_id},
                "page": {"start": 0, "limit": 200, "sort": ""},
            }
            rows.extend(self._call(self.client.cc.search_module, params))
        return self._merge_same_name_rows(rows, "bk_module_id", "bk_module_name", "bk_module_ids")

    def list_hosts(self, filters):
        params = {
            "bk_biz_id": filters.get("bk_biz_id"),
            "page": {"start": 0, "limit": 200},
            "fields": [
                "bk_host_id",
                "bk_host_innerip",
                "bk_host_name",
                "bk_os_name",
                "bk_cpu",
                "bk_mem",
                "operator",
                "bk_bak_operator",
            ],
        }
        if filters.get("bk_set_ids"):
            params["bk_set_ids"] = filters["bk_set_ids"]
        if filters.get("bk_module_ids"):
            params["bk_module_ids"] = filters["bk_module_ids"]
        host_filter = self._host_property_filter(filters)
        if host_filter["rules"]:
            params["host_property_filter"] = host_filter
        return self._call(self.client.cc.list_biz_hosts, params)

    def get_host_detail(self, host_id):
        params = {
            "bk_host_id": host_id,
        }
        result = self._call_raw(self.client.cc.get_host_base_info, params)
        data = result.get("data")
        if isinstance(data, list):
            return self._clean_detail_rows(data)
        if isinstance(data, dict):
            rows = data.get("info")
            if isinstance(rows, list):
                return self._clean_detail_rows(rows)
            return self._clean_detail_dict(data)
        return None

    def _call(self, api, params):
        result = self._call_raw(api, params)
        data = result.get("data") or {}
        rows = data.get("info") if isinstance(data, dict) else data
        return rows or []

    def _call_raw(self, api, params):
        try:
            result = api(params)
        except Exception as err:
            logger.exception("CMDB API call failed")
            raise CmdbServiceError("CMDB request failed. Please check CMDB access and retry.") from err
        if not result.get("result"):
            message = result.get("message") or "CMDB request returned an error."
            logger.warning("CMDB API returned error: %s", message)
            raise CmdbServiceError(message)
        return result

    def _host_property_filter(self, filters):
        host_filter = {"condition": "AND", "rules": []}
        for field in ("bk_host_name", "operator", "bk_bak_operator", "bk_host_innerip"):
            value = filters.get(field)
            if value:
                host_filter["rules"].append(
                    {"field": field, "operator": "equal", "value": value}
                )
        return host_filter

    def _is_demo_business(self, row):
        name = str(row.get("bk_biz_name", "")).lower()
        return all(marker in name for marker in DEMO_BUSINESS_MARKERS)

    def _is_hidden_set(self, row):
        name = str(row.get("bk_set_name", "")).lower()
        return any(marker in name for marker in HIDDEN_SET_MARKERS)

    def _merge_same_name_rows(self, rows, id_key, name_key, ids_key):
        merged = {}
        order = []
        for row in rows:
            name = str(row.get(name_key, "")).strip()
            normalized = name.lower()
            if normalized not in merged:
                merged[normalized] = {**row, ids_key: [row[id_key]]}
                order.append(normalized)
            else:
                merged[normalized][ids_key].append(row[id_key])
        result = []
        for normalized in order:
            row = merged[normalized]
            ids = row[ids_key]
            row[id_key] = ids[0] if len(ids) == 1 else ",".join(str(value) for value in ids)
            result.append(row)
        return result

    def _clean_detail_rows(self, rows):
        cleaned = []
        for row in rows:
            field_id = row.get("bk_property_id")
            value = row.get("bk_property_value")
            if field_id in HOST_DETAIL_FIELD_ALLOWLIST and self._has_detail_value(value):
                cleaned.append(row)
        return cleaned

    def _clean_detail_dict(self, data):
        return {
            key: value
            for key, value in data.items()
            if key in HOST_DETAIL_FIELD_ALLOWLIST and self._has_detail_value(value)
        }

    def _has_detail_value(self, value):
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() not in EMPTY_DETAIL_VALUES
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True
