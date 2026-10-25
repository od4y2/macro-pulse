"""China healthcare geography records for the RQ3 case study (unit S12).

The bounded case: when a provincial medical-insurance platform suspends
settlement, the exposure is geographic - every designated hospital and
pharmacy in the province loses networked payment at once. This module
holds the officially verified resource records that quantify that
exposure, and makes the missingness explicit: the registry records only
what was directly verified from official documents; every other
provincial region is named NOT recorded, never imputed.

Records are verified in two passes:

- Pass 1 (S12, verified live 2026-08-29; verbatim quotes and
  PDF-extraction output in ``evidence/S12/live-verification.md``):
  CHN national 2023 (National Health Commission 2023 statistical
  bulletin, machine-extracted from the official PDF), Beijing 2023,
  Yunnan 2023.
- Pass 2 (S20, verified live 2026-10-11..16 per the full-data-coverage
  go-live directive; verbatim quotes, URLs, access methods, and the
  operator verification log in ``evidence/S20/province-verification.md``):
  the 29 previously unrecorded provinces - completing all 31
  provincial-level divisions. 91 records total.

Source hierarchy (recorded per record, never smoothed over):

- Where a provincial health commission publishes a machine-verifiable
  annual release (统计公报 or equivalent official annual release), it is
  primary. Where it does not, the provincial economic/statistical
  bulletin (国民经济和社会发展统计公报) is used and its 资料来源
  attribution to the health commission is recorded.
- A metric absent from the primary but present in another official
  release is encoded as a separate record carrying that release's own
  citation (e.g. Zhejiang's 2024 per-1,000 from the commission's
  statistical table; Hebei's 2025 per-1,000 from the commission's
  performance self-assessment).
- 万 (10,000) units are converted exactly; per-万 rates are NEVER
  rescaled into the per-1,000 metric (Shanghai and Jilin publish only
  per-万 rates on non-comparable denominators - not encoded).
- Scanned or image-only official documents (Shaanxi, Gansu, Ningxia)
  are extracted via OCR; the OCR caveat is recorded per record and
  figures are cross-validated arithmetically and against adjacent-year
  editions before encoding.

Comparability caveats (recorded per record, never pooled silently):

- Record years span 2022-2025 across provinces; the exposure report
  carries record_year next to every figure and never implies
  at-episode-year values.
- Bed measures differ: AUTHORIZED (编制), ACTUAL (实有), ACTUALLY-OPEN
  (实际开放), or unspecified - each record's notes state the measure.
- Institution scope differs: village clinics are included in some
  provinces (Tibet, Gansu, Shanghai state it) and EXCLUDED in Jiangxi;
  some hospital counts exclude 妇幼保健院/机构 (Guangdong, Guizhou);
  Jiangxi's bed count covers 医院、卫生院 only.
- Per-1,000 denominators differ: resident population (常住人口) in most
  records, unqualified 人口 in others; 11 provinces publish no
  per-1,000 figure at all in the encoded sources.
- Some economic-bulletin figures are preliminary (初步统计数) or rounded
  (Fujian 2025: 3.10万个 / 25.40万张); the flags are carried in notes.
- Yunnan's latest verified record year (2023) PREDATES the registry's
  episodes (2024+): the exposure report states the record year next to
  the numbers rather than implying they are at-episode-year figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macropulse.case_study.episodes import Episode
from macropulse.scope import EVIDENCE_LABELS

RECORD_EVIDENCE_LABEL = "external"

# Closed metric vocabulary. Each metric's measure is pinned so records
# with different underlying measures cannot be silently pooled.
PROVINCIAL_METRICS = (
    "institutions",  # medical & health institutions (count)
    "beds",  # total institution beds (count); see notes for authorized vs actual
    "beds_per_1000",  # beds per 1,000 population; see notes for the measure
)

# China's 31 provincial-level divisions (NHC bulletin coverage; HK/MO/TW
# are reported separately in source publications and are out of scope).
# This is the closed region vocabulary for named missingness.
PROVINCES = (
    "Beijing",
    "Tianjin",
    "Hebei",
    "Shanxi",
    "Inner Mongolia",
    "Liaoning",
    "Jilin",
    "Heilongjiang",
    "Shanghai",
    "Jiangsu",
    "Zhejiang",
    "Anhui",
    "Fujian",
    "Jiangxi",
    "Shandong",
    "Henan",
    "Hubei",
    "Hunan",
    "Guangdong",
    "Guangxi",
    "Hainan",
    "Chongqing",
    "Sichuan",
    "Guizhou",
    "Yunnan",
    "Shaanxi",
    "Gansu",
    "Qinghai",
    "Ningxia",
    "Xinjiang",
    "Tibet",
)

# Case-study subset of the panel (RQ3 scope: a bounded case, not the
# whole panel).
CASE_STUDY_COUNTRIES = ("CHN",)


@dataclass(frozen=True)
class ResourceRecord:
    """One officially verified healthcare-resource figure for one region.

    Citation fields (source_name, source_title, source_url, published)
    are mandatory, same rule as episodes: a number without a source is a
    fabrication. ``notes`` records measure-definition caveats.
    """

    region: str  # province name, or "CHN" for the national record
    metric: str  # PROVINCIAL_METRICS
    value: float
    year: int
    source_name: str
    source_title: str
    source_url: str
    published: date
    notes: str = ""
    evidence_label: str = RECORD_EVIDENCE_LABEL

    def __post_init__(self) -> None:
        if self.metric not in PROVINCIAL_METRICS:
            raise ValueError(f"metric {self.metric!r} not in {PROVINCIAL_METRICS}")
        if self.region != "CHN" and self.region not in PROVINCES:
            raise ValueError(f"unknown region: {self.region!r}")
        if self.value <= 0:
            raise ValueError(f"{self.region} {self.metric}: value must be positive")
        if not (2010 <= self.year <= 2030):
            raise ValueError(
                f"{self.region} {self.metric}: implausible year {self.year}"
            )
        for field_name in ("source_name", "source_title", "source_url"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(
                    f"{self.region} {self.metric}: {field_name} citation is "
                    "mandatory - an uncited figure is a fabrication"
                )
        if self.source_url and not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"{self.region} {self.metric}: source_url must be http(s)")
        if self.evidence_label not in EVIDENCE_LABELS:
            raise ValueError(
                f"{self.region} {self.metric}: evidence_label "
                f"{self.evidence_label!r} not in the S01 vocabulary"
            )
        if self.evidence_label != RECORD_EVIDENCE_LABEL:
            raise ValueError(
                f"{self.region} {self.metric}: case-study records are external "
                f"documents - label must be {RECORD_EVIDENCE_LABEL!r}"
            )


# --- verified records (live, 2026-08-29) --------------------------------------

_NHC_2023_URL = (
    "https://www.nhc.gov.cn/wjw/c100178/202408/"
    "1de460738f81464280e9ed3277630e33/files/1734002454304_67772.pdf"
)
_BJ_2023_URL = "http://www.phic.org.cn/tjsj/wstjgb/202408/P020240819586687344254.pdf"
_YNDAILY_URL = "https://www.yndaily.com/html/2024/yaowenyunnan_0925/129208.html"

# --- S20 province-expansion source URLs (verified live 2026-10-11..16) --------
_TJ_2025_ECON = "https://stats.tj.gov.cn/tjsj_52032/tjgb/202603/t20260323_7267486.html"
_HB_2025_ECON = "https://www.hebei.gov.cn/columns/3bbf017c-0e27-4cac-88c0-c5cac90ecd73/202604/14/39058c18-8d16-4a19-ab71-6d1bf8d2749f.html"
_HB_2025_ZIPING = "http://wsjkw.hebei.gov.cn/czyjs/419541.jhtml"
_SX_2024_URL = "https://wjw.shanxi.gov.cn/zfxxgk/fdzdgknr/ghjh/202602/P020260206603605483382.pdf"
_NMG_2025_URL = "http://wjw.nmg.gov.cn/zfxxgk/fdzzgknr/tjxx/nb/202606/t20260612_2915713.html"
_LN_2025_ECON = "https://tjj.ln.gov.cn/tjj/articleFileDir/2026-03/31/7d0ebeac0ed3499da6e4aa0f94acf972/2026033115100327617.pdf"
_JL_2025_ECON = "http://tjj.jl.gov.cn/tjsj/tjgb/ndgb/202604/t20260427_3627028.html"
_HLJ_2025_ECON = "https://tjj.hlj.gov.cn/tjj/c106779/202603/c00_31925539.shtml"
_SH_2024_URL = "https://wsjkw.sh.gov.cn/2024wsjkzkbg/20251208/4fe2a4a9f0b54351984aa066777c05fb.html"
_JS_2023_URL = "http://wjw.jiangsu.gov.cn/module/download/downfile.jsp?classid=0&filename=5bf41d52c7ac47b0a369b4b4d9285f3e.pdf"
_ZJ_2025_ECON = "https://tjj.zj.gov.cn/col/col1229129205/art/2026/art_724c5ad52b8c4ac89def939cb9dee18c.html"
_ZJ_2025_INST = "https://wsjkw.zj.gov.cn/col/col1229123426/art/2026/art_9d8eafccdf664d49833541f77a09b582.html"
_ZJ_2024_PER1000 = "https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web2787/site/attach/0/975f8dccbdc04e96abd6f6e042a8ba7f.pdf"
_AH_2024_URL = "https://wjw.ah.gov.cn/group4/M00/08/C2/wKg862kEeaaAQvaXAAjrongELhI404.pdf"
_FJ_2022_URL = "https://wjw.fj.gov.cn/jggk/csxx/ghyxxc/xxtj_41288/202310/t20231023_6280147.htm"
_FJ_2025_ECON = "https://tjj.fj.gov.cn/xxgk/tjgb/202603/t20260313_7109476.htm"
_FJ_2024_PER1000 = "https://wjw.fujian.gov.cn/jggk/csxx/bgs/gzdt/202510/t20251013_7020368.htm"
_JX_2025_ECON = "https://www.jiangxi.gov.cn/jxsrmzf/zxfb/pc/content/content_2037309510965067776.html"
_SD_2024_URL = "http://wsjkw.shandong.gov.cn/zwgk/fdzdgknr/tjgb/202512/P020251217356715592186.pdf"
_HA_2025_ECON = "https://tjj.henan.gov.cn/2026/04-09/3341308.html"
_HUB_2025_ECON = "https://tjj.hubei.gov.cn/tjsj/tjgb/ndtjgb/qstjgb/202603/t20260318_5894639.shtml"
_HUN_2024_URL = "https://wjw.hunan.gov.cn/wjw/xxgk/tzgg/202601/33901702/files/3c6a647af6ef4ba7ba53f62d8393455c.pdf"
_GD_2025_URL = "https://wsjkw.gd.gov.cn/gkmlpt/content/4/4907/mpost_4907189.html"
_GX_2024_URL = "https://wsjkw.gxzf.gov.cn/xxgk_49493/fdzdgk/tjxx/tjnb/t26240378.shtml"
_HAIN_2023_URL = "https://wst.hainan.gov.cn/swjw/xxgk/0900/202411/t20241122_3773173.html"
_CQ_2025_URL = "https://wsjkw.cq.gov.cn/zwgk_242/fdzdgknr/tjxx/tjfx/202608/W020260825529766743577.pdf"
_SC_2024_URL = "https://wsjkw.sc.gov.cn/scwsjkw/njgb/2026/2/9/821f77b263a044498965f82e3b035625.shtml"
_GZ_2023_URL = "https://wjw.guizhou.gov.cn/zwgk/zdlyxx/tjsj/202409/t20240925_85752730.html"
_GZ_2025_TABLE = "https://wjw.guizhou.gov.cn/zwgk/zdlyxx/tjsj/202605/t20260519_90187411.html"
_XZ_2025_URL = "https://wjw.xizang.gov.cn/zwgk/msggk/jktongji/202605/P020260514396224265562.pdf"
_SNX_2025_URL = "https://sxwjw.shaanxi.gov.cn/zfxxgk/fdzdgknr/tjxx/P020260810289621239421.pdf"
_GS_2023_URL = "http://wjw.pingliang.gov.cn/api-gateway/jpaas-web-server/front/document/download?fileUrl=YW5UzzlvCwcM%2FNHHX%2FtT6HhnILUYEuE4XKZMlTIXaXXVpClpPglLhXCuwXzLou4SJUsirtvM6eYjnzYfMi2On92on0msZ5Ku7PMC6I%2BajE%2Fb06LZoiascJajaQn%2BXuR8yYi%2BEU%2BpmXIAhW5B6qAk9Eg%2Bxgbnhm2Q19hYAdU%2BAg8%3D&fileName=2023%E5%B9%B4%E7%94%98%E8%82%83%E7%9C%81%E5%8D%AB%E7%94%9F%E5%81%A5%E5%BA%B7%E4%BA%8B%E4%B8%9A%E5%8F%91%E5%B1%95%E7%BB%9F%E8%AE%A1%E5%85%AC%E6%8A%A5.pdf"
_QH_2025_ECON = "http://tjj.qinghai.gov.cn/tjData/yearBulletin/202603/P020260302663152872943.doc"
_NX_2025_URL = "https://wsjkw.nx.gov.cn/zfxxgk_279/fdzdgknr/wstjbg/202606/t20260625_5274257.html"
_XJ_2024_URL = "https://wjw.xinjiang.gov.cn/hfpc/xwxc1/202507/8084e94da5b44ca9a8a3dc5a6f1a9759.shtml"

VERIFIED_RECORDS: tuple[ResourceRecord, ...] = (
    # National 2023, NHC 2023 statistical bulletin (PDF text extraction):
    # "2023年末，全国医疗卫生机构总数 1070785 个" / "全国医疗卫生机构床位
    # 1017.4 万张" / "每千人口医疗卫生机构床位数由 2022 年 6.92 张增加到
    # 2023 年 7.23 张"
    ResourceRecord(
        region="CHN",
        metric="institutions",
        value=1_070_785,
        year=2023,
        source_name="National Health Commission (China)",
        source_title="2023年我国卫生健康事业发展统计公报",
        source_url=_NHC_2023_URL,
        published=date(2024, 8, 26),
        notes="National total, all medical & health institutions.",
    ),
    ResourceRecord(
        region="CHN",
        metric="beds",
        value=10_174_000,  # 1017.4 万张
        year=2023,
        source_name="National Health Commission (China)",
        source_title="2023年我国卫生健康事业发展统计公报",
        source_url=_NHC_2023_URL,
        published=date(2024, 8, 26),
        notes="National total institution beds (床位), not authorized beds.",
    ),
    ResourceRecord(
        region="CHN",
        metric="beds_per_1000",
        value=7.23,
        year=2023,
        source_name="National Health Commission (China)",
        source_title="2023年我国卫生健康事业发展统计公报",
        source_url=_NHC_2023_URL,
        published=date(2024, 8, 26),
        notes="Beds per 1,000 population, total institution beds (2022: 6.92).",
    ),
    # Beijing 2023, Beijing 2023 health development statistical bulletin
    # (PDF text extraction): "机构数达 12518 家" / "全市医疗机构编制床位总数达
    # 149971 张" / "每千常住人口医疗机构编制床位 6.87 张"
    ResourceRecord(
        region="Beijing",
        metric="institutions",
        value=12_518,
        year=2023,
        source_name="Beijing Municipal Health Commission",
        source_title="2023年北京市卫生健康事业发展统计公报",
        source_url=_BJ_2023_URL,
        published=date(2024, 8, 19),
        notes="Medical & health institutions incl. 12,298 medical institutions.",
    ),
    ResourceRecord(
        region="Beijing",
        metric="beds",
        value=149_971,
        year=2023,
        source_name="Beijing Municipal Health Commission",
        source_title="2023年北京市卫生健康事业发展统计公报",
        source_url=_BJ_2023_URL,
        published=date(2024, 8, 19),
        notes="AUTHORIZED beds (编制床位); actual beds (实有) 138,825.",
    ),
    ResourceRecord(
        region="Beijing",
        metric="beds_per_1000",
        value=6.87,
        year=2023,
        source_name="Beijing Municipal Health Commission",
        source_title="2023年北京市卫生健康事业发展统计公报",
        source_url=_BJ_2023_URL,
        published=date(2024, 8, 19),
        notes=(
            "AUTHORIZED beds per 1,000 permanent residents (编制); actual "
            "(实有) 6.35. Not comparable to the national total-bed rate."
        ),
    ),
    # Yunnan 2023, Yunnan Daily (2024-09-25) reporting provincial health
    # statistics: "截至2023年，全省共有医疗卫生机构28765个、医疗卫生机构
    # 拥有床位数35.99万张"
    ResourceRecord(
        region="Yunnan",
        metric="institutions",
        value=28_765,
        year=2023,
        source_name="Yunnan Daily (reporting provincial health-commission data)",
        source_title="筑基强本守护人民健康",
        source_url=_YNDAILY_URL,
        published=date(2024, 9, 25),
        notes=(
            "Province-wide institutions. The commission's own 2024 bulletin "
            "PDF was unreachable (SSL handshake failure) - not recorded."
        ),
    ),
    ResourceRecord(
        region="Yunnan",
        metric="beds",
        value=359_900,  # 35.99 万张
        year=2023,
        source_name="Yunnan Daily (reporting provincial health-commission data)",
        source_title="筑基强本守护人民健康",
        source_url=_YNDAILY_URL,
        published=date(2024, 9, 25),
        notes="Province-wide institution beds; includes 275,778 hospital beds.",
    ),
    # --- S20 expansion: the 29 previously unrecorded provinces ---------------------
    # (verified live 2026-10-11..16; verbatim quotes, access methods, and
    # cross-validation logs in evidence/S20/province-verification.md)
    #
    # Tianjin 2025, municipal economic bulletin: "年末全市共有各类卫生机构
    # 7415个，其中医院451个。" / "卫生机构床位7.49万张，其中医院床位6.92万张。"
    ResourceRecord(
        region="Tianjin",
        metric="institutions",
        value=7_415,
        year=2025,
        source_name="Tianjin Municipal Bureau of Statistics",
        source_title="2025年天津市国民经济和社会发展统计公报",
        source_url=_TJ_2025_ECON,
        published=date(2026, 3, 23),
        notes=(
            "Economic bulletin (the commission publishes no standalone health "
            "bulletin); 各类卫生机构 wording; health data attributed to the "
            "municipal health commission per the bulletin's 资料来源 note; "
            "no per-1,000 figure exists in the source."
        ),
    ),
    ResourceRecord(
        region="Tianjin",
        metric="beds",
        value=74_900,  # 7.49 万张
        year=2025,
        source_name="Tianjin Municipal Bureau of Statistics",
        source_title="2025年天津市国民经济和社会发展统计公报",
        source_url=_TJ_2025_ECON,
        published=date(2026, 3, 23),
        notes="Economic bulletin; 卫生机构床位 (measure unspecified beyond that).",
    ),
    # Hebei 2025, provincial economic bulletin: "年末医疗卫生机构93687个" /
    # "医疗卫生机构床位54.34万张"; per-1,000 from the commission's own
    # performance self-assessment: "每千人口医疗卫生机构床位数7.39张左右"
    ResourceRecord(
        region="Hebei",
        metric="institutions",
        value=93_687,
        year=2025,
        source_name="Hebei Provincial Bureau of Statistics (via hebei.gov.cn)",
        source_title="河北省2025年国民经济和社会发展统计公报",
        source_url=_HB_2025_ECON,
        published=date(2026, 4, 13),
        notes=(
            "Economic bulletin, PRELIMINARY (初步统计数 per bulletin note 1); "
            "health data attributed to 省卫生健康委员会 per 资料来源."
        ),
    ),
    ResourceRecord(
        region="Hebei",
        metric="beds",
        value=543_400,  # 54.34 万张
        year=2025,
        source_name="Hebei Provincial Bureau of Statistics (via hebei.gov.cn)",
        source_title="河北省2025年国民经济和社会发展统计公报",
        source_url=_HB_2025_ECON,
        published=date(2026, 4, 13),
        notes=(
            "Economic bulletin, PRELIMINARY (初步统计数); bed measure "
            "(编制/实有) not distinguished in the source."
        ),
    ),
    ResourceRecord(
        region="Hebei",
        metric="beds_per_1000",
        value=7.39,
        year=2025,
        source_name="Hebei Provincial Health Commission",
        source_title="河北省卫生健康委2025年度部门绩效自评情况公开",
        source_url=_HB_2025_ZIPING,
        published=date(2026, 5, 18),
        notes=(
            "Stated as approximate (7.39张左右, as printed); separate official "
            "release from the commission used because the economic bulletin "
            "carries no per-1,000 figure; underlying 2025 data are preliminary."
        ),
    ),
    # Shanxi 2024, provincial health bulletin (PDF text extraction):
    # "全省共有医疗卫生机构 38431 个" / "床位 22.99 万张" /
    # "每千常住人口医疗卫生机构床位数 6.67 张"
    ResourceRecord(
        region="Shanxi",
        metric="institutions",
        value=38_431,
        year=2024,
        source_name="Shanxi Provincial Health Commission",
        source_title="2024年山西省卫生健康事业发展统计公报",
        source_url=_SX_2024_URL,
        published=date(2026, 2, 6),
        notes="Province-wide (全省), year 2024.",
    ),
    ResourceRecord(
        region="Shanxi",
        metric="beds",
        value=229_900,  # 22.99 万张
        year=2024,
        source_name="Shanxi Provincial Health Commission",
        source_title="2024年山西省卫生健康事业发展统计公报",
        source_url=_SX_2024_URL,
        published=date(2026, 2, 6),
        notes="万张 converted exactly (22.99万 = 229,900).",
    ),
    ResourceRecord(
        region="Shanxi",
        metric="beds_per_1000",
        value=6.67,
        year=2024,
        source_name="Shanxi Provincial Health Commission",
        source_title="2024年山西省卫生健康事业发展统计公报",
        source_url=_SX_2024_URL,
        published=date(2026, 2, 6),
        notes="Per 1,000 RESIDENT population (每千常住人口).",
    ),
    # Inner Mongolia 2025, regional health bulletin (page text):
    # "全区卫生机构总数达26914个" / "共有床位171421张" /
    # "每千人口医疗卫生机构床位数由2024年的7.27张降低到2025年的7.22张"
    ResourceRecord(
        region="Inner Mongolia",
        metric="institutions",
        value=26_914,
        year=2025,
        source_name="Health Commission of Inner Mongolia Autonomous Region",
        source_title="2025年内蒙古自治区卫生健康事业发展统计公报",
        source_url=_NMG_2025_URL,
        published=date(2026, 6, 12),
        notes=(
            "Institution sentence uses 卫生机构 wording; footnote 1 defines "
            "the institution scope."
        ),
    ),
    ResourceRecord(
        region="Inner Mongolia",
        metric="beds",
        value=171_421,
        year=2025,
        source_name="Health Commission of Inner Mongolia Autonomous Region",
        source_title="2025年内蒙古自治区卫生健康事业发展统计公报",
        source_url=_NMG_2025_URL,
        published=date(2026, 6, 12),
        notes="Year-end 2025 beds.",
    ),
    ResourceRecord(
        region="Inner Mongolia",
        metric="beds_per_1000",
        value=7.22,
        year=2025,
        source_name="Health Commission of Inner Mongolia Autonomous Region",
        source_title="2025年内蒙古自治区卫生健康事业发展统计公报",
        source_url=_NMG_2025_URL,
        published=date(2026, 6, 12),
        notes="Per footnote 13, computed on RESIDENT population (常住人口) "
        "from the regional statistics bureau.",
    ),
    # Liaoning 2025, provincial economic bulletin (PDF text extraction):
    # "年末有医疗卫生机构37678个。" / "年末医疗卫生机构拥有床位33.1万张"
    ResourceRecord(
        region="Liaoning",
        metric="institutions",
        value=37_678,
        year=2025,
        source_name="Liaoning Provincial Bureau of Statistics",
        source_title="辽宁省2025年国民经济和社会发展统计公报",
        source_url=_LN_2025_ECON,
        published=date(2026, 3, 31),
        notes=(
            "Economic bulletin (the commission's site has no statistical-"
            "bulletin category); 卫生数据来自省卫生健康委员会 per 资料来源."
        ),
    ),
    ResourceRecord(
        region="Liaoning",
        metric="beds",
        value=331_000,  # 33.1 万张
        year=2025,
        source_name="Liaoning Provincial Bureau of Statistics",
        source_title="辽宁省2025年国民经济和社会发展统计公报",
        source_url=_LN_2025_ECON,
        published=date(2026, 3, 31),
        notes=(
            "Economic bulletin; no per-1,000 figure in the source (a third-"
            "party ~7.9 estimate exists and is NOT used)."
        ),
    ),
    # Jilin 2025, provincial economic bulletin: "医疗卫生机构实有床位18.09万张。"
    # (beds only - the bulletin contains no institution count)
    ResourceRecord(
        region="Jilin",
        metric="beds",
        value=180_900,  # 18.09 万张
        year=2025,
        source_name="Jilin Provincial Bureau of Statistics",
        source_title="吉林省2025年国民经济和社会发展统计公报",
        source_url=_JL_2025_ECON,
        published=date(2026, 4, 27),
        notes=(
            "ACTUAL beds (实有床位), year-end preliminary (年末预计); the "
            "bulletin contains no institution count and no per-1,000 figure. "
            "The statistical yearbook's per-万 rate (76.7/万) is NOT rescaled "
            "into the per-1,000 metric."
        ),
    ),
    # Heilongjiang 2025, provincial economic bulletin: "初步统计，全省共有
    # 医疗卫生机构22867个" / "医疗卫生机构实有床位数23.77万张"
    ResourceRecord(
        region="Heilongjiang",
        metric="institutions",
        value=22_867,
        year=2025,
        source_name="Heilongjiang Provincial Bureau of Statistics",
        source_title="2025年黑龙江省国民经济和社会发展统计公报",
        source_url=_HLJ_2025_ECON,
        published=date(2026, 3, 31),
        notes="Economic bulletin, PRELIMINARY (初步统计), province-wide.",
    ),
    ResourceRecord(
        region="Heilongjiang",
        metric="beds",
        value=237_700,  # 23.77 万张
        year=2025,
        source_name="Heilongjiang Provincial Bureau of Statistics",
        source_title="2025年黑龙江省国民经济和社会发展统计公报",
        source_url=_HLJ_2025_ECON,
        published=date(2026, 3, 31),
        notes=(
            "ACTUAL beds (实有床位), PRELIMINARY (初步统计); no per-1,000 "
            "figure in the source."
        ),
    ),
    # Shanghai 2024, commission annual report: "全市各级各类医疗卫生机构总数
    # 达6431所（含村卫生室）" / "全市医疗机构实际开放床位19.39万张"
    ResourceRecord(
        region="Shanghai",
        metric="institutions",
        value=6_431,
        year=2024,
        source_name="Shanghai Municipal Health Commission",
        source_title="上海市卫生健康状况报告（2024）",
        source_url=_SH_2024_URL,
        published=date(2025, 12, 8),
        notes=(
            "Institutions INCLUDE village clinics (含村卫生室); measured in 所. "
            "2024 edition is the newest (2025 edition not yet published)."
        ),
    ),
    ResourceRecord(
        region="Shanghai",
        metric="beds",
        value=193_900,  # 19.39 万张
        year=2024,
        source_name="Shanghai Municipal Health Commission",
        source_title="上海市卫生健康状况报告（2024）",
        source_url=_SH_2024_URL,
        published=date(2025, 12, 8),
        notes=(
            "ACTUALLY-OPEN beds (实际开放床位) - a different measure from "
            "authorized or actual; scope is 医疗机构. The 2025 statistics "
            "page's per-万 registered-population rate (130.5/万, 户籍) is a "
            "non-comparable basis and is NOT encoded."
        ),
    ),
    # Jiangsu 2023, provincial health bulletin (PDF text extraction):
    # "全省医疗卫生机构总数 39543 个" / "全省医疗机构床位 578826 张" /
    # "全省每千人口床位数 6.79 张"
    ResourceRecord(
        region="Jiangsu",
        metric="institutions",
        value=39_543,
        year=2023,
        source_name="Jiangsu Provincial Health Commission",
        source_title="2023年江苏省卫生健康事业发展统计公报",
        source_url=_JS_2023_URL,
        published=date(2024, 6, 14),
        notes=(
            "Year-end 2023 (年末). The PDF download URL carries no date; the "
            "hosting article (wjw.jiangsu.gov.cn/art/2024/6/14/"
            "art_55455_11270950.html) is dated 2024-06-14."
        ),
    ),
    ResourceRecord(
        region="Jiangsu",
        metric="beds",
        value=578_826,
        year=2023,
        source_name="Jiangsu Provincial Health Commission",
        source_title="2023年江苏省卫生健康事业发展统计公报",
        source_url=_JS_2023_URL,
        published=date(2024, 6, 14),
        notes=(
            "Bed sentence scope is 医疗机构 (medical institutions) rather "
            "than 医疗卫生机构 - wording differs slightly from other "
            "provinces; year-end 2023."
        ),
    ),
    ResourceRecord(
        region="Jiangsu",
        metric="beds_per_1000",
        value=6.79,
        year=2023,
        source_name="Jiangsu Provincial Health Commission",
        source_title="2023年江苏省卫生健康事业发展统计公报",
        source_url=_JS_2023_URL,
        published=date(2024, 6, 14),
        notes="每千人口床位数 (population base unqualified in the source).",
    ),
    # Zhejiang 2025 institutions, commission statistical table (PDF text
    # extraction): row "总 计 40343 1643 ... 38107"; 2025 beds from the
    # economic bulletin: "医疗卫生机构床位数42.1万张"; 2024 per-1,000 from
    # the commission's table: "全 省 ... 6670 6.19" (床位413193张, 常住 6670万)
    ResourceRecord(
        region="Zhejiang",
        metric="institutions",
        value=40_343,
        year=2025,
        source_name="Zhejiang Provincial Health Commission",
        source_title="2025年浙江省各地区医疗卫生机构数",
        source_url=_ZJ_2025_INST,
        published=date(2026, 6, 11),
        notes=(
            "Exact commission count (40,343); the economic bulletin's rounded "
            "4.03万个 is consistent. The commission publishes statistical "
            "tables, not a bulletins series."
        ),
    ),
    ResourceRecord(
        region="Zhejiang",
        metric="beds",
        value=421_000,  # 42.1 万张
        year=2025,
        source_name="Zhejiang Provincial Bureau of Statistics",
        source_title="2025年浙江省国民经济和社会发展统计公报",
        source_url=_ZJ_2025_ECON,
        published=date(2026, 3, 3),
        notes=(
            "Economic bulletin; rounded 万 figure as printed (42.1万 = "
            "421,000); measure wording 医疗卫生机构床位数."
        ),
    ),
    ResourceRecord(
        region="Zhejiang",
        metric="beds_per_1000",
        value=6.19,
        year=2024,
        source_name="Zhejiang Provincial Health Commission",
        source_title="2024年全省各地区每千人口床位、人员、医生、护士数（常住）",
        source_url=_ZJ_2024_PER1000,
        published=date(2025, 6, 20),
        notes=(
            "RESIDENT population (常住) denominator: beds 413,193 on 66.70M "
            "residents; institutions and staff include village clinics per "
            "the table's footnote. The commission's 2025 per-1,000 table is "
            "an image-only scan (not machine-readable) - the 2025 rate is "
            "not encoded."
        ),
    ),
    # Anhui 2024, provincial health bulletin (PDF text extraction):
    # "全省医疗卫生机构数达 32635 个" / "全省医疗卫生机构床位 44.9 万张" /
    # "每千人口医疗卫生机构床位数由 2023 年 7.41 张下降至 7.33 张"
    ResourceRecord(
        region="Anhui",
        metric="institutions",
        value=32_635,
        year=2024,
        source_name="Anhui Provincial Health Commission",
        source_title="2024年安徽省卫生健康事业发展统计公报",
        source_url=_AH_2024_URL,
        published=date(2025, 10, 31),
        notes=(
            "Year-end 2024 (年末). The PDF URL is hash-based (no date); the "
            "hosting article (wjw.ah.gov.cn/public/7001/58031321.html) is "
            "dated 2025-10-31."
        ),
    ),
    ResourceRecord(
        region="Anhui",
        metric="beds",
        value=449_000,  # 44.9 万张
        year=2024,
        source_name="Anhui Provincial Health Commission",
        source_title="2024年安徽省卫生健康事业发展统计公报",
        source_url=_AH_2024_URL,
        published=date(2025, 10, 31),
        notes="万张 converted exactly (44.9万 = 449,000); year-end 2024.",
    ),
    ResourceRecord(
        region="Anhui",
        metric="beds_per_1000",
        value=7.33,
        year=2024,
        source_name="Anhui Provincial Health Commission",
        source_title="2024年安徽省卫生健康事业发展统计公报",
        source_url=_AH_2024_URL,
        published=date(2025, 10, 31),
        notes=(
            "Given as a 2023-to-2024 change endpoint (7.41 -> 7.33); "
            "population base unqualified (每千人口)."
        ),
    ),
    # Fujian 2022, commission annual statistical release: "全省医疗卫生机构总数
    # 29117个" / "床位总数232425张" / "由2021年5.35张增加到2022年5.55张";
    # 2025 econ bulletin: "医疗卫生机构3.10万个" / "医疗机构床位25.40万张";
    # 2024 per-1,000 via commission-republished Health News article: "全省每千
    # 人口医疗机构床位数...达到5.94张"
    ResourceRecord(
        region="Fujian",
        metric="institutions",
        value=29_117,
        year=2022,
        source_name="Fujian Provincial Health Commission",
        source_title="2022年福建省医疗卫生资源及医疗服务情况",
        source_url=_FJ_2022_URL,
        published=date(2023, 10, 23),
        notes=(
            "The commission publishes no 统计公报-titled document; this "
            "annual release is its official statistical publication. The "
            "2022 edition is the newest with machine-readable text (2023-"
            "2025 tables are image-only)."
        ),
    ),
    ResourceRecord(
        region="Fujian",
        metric="beds",
        value=232_425,
        year=2022,
        source_name="Fujian Provincial Health Commission",
        source_title="2022年福建省医疗卫生资源及医疗服务情况",
        source_url=_FJ_2022_URL,
        published=date(2023, 10, 23),
        notes="ACTUAL beds (实有床位总数), year-end 2022; table 1 same scope.",
    ),
    ResourceRecord(
        region="Fujian",
        metric="beds_per_1000",
        value=5.55,
        year=2022,
        source_name="Fujian Provincial Health Commission",
        source_title="2022年福建省医疗卫生资源及医疗服务情况",
        source_url=_FJ_2022_URL,
        published=date(2023, 10, 23),
        notes="Change endpoint 2021 (5.35) -> 2022 (5.55).",
    ),
    ResourceRecord(
        region="Fujian",
        metric="institutions",
        value=31_000,  # 3.10 万个, rounded
        year=2025,
        source_name="Fujian Provincial Bureau of Statistics",
        source_title="2025年福建省国民经济和社会发展统计公报",
        source_url=_FJ_2025_ECON,
        published=date(2026, 3, 19),
        notes=(
            "Economic bulletin; ROUNDED as printed (3.10万个 = 31,000); "
            "no per-1,000 figure in the source."
        ),
    ),
    ResourceRecord(
        region="Fujian",
        metric="beds",
        value=254_000,  # 25.40 万张, rounded
        year=2025,
        source_name="Fujian Provincial Bureau of Statistics",
        source_title="2025年福建省国民经济和社会发展统计公报",
        source_url=_FJ_2025_ECON,
        published=date(2026, 3, 19),
        notes=(
            "Economic bulletin; ROUNDED as printed (25.40万张 = 254,000); "
            "measure wording 医疗机构床位."
        ),
    ),
    ResourceRecord(
        region="Fujian",
        metric="beds_per_1000",
        value=5.94,
        year=2024,
        source_name="Fujian Provincial Health Commission (republishing Health News)",
        source_title="福建：力推三明医改 实施健康优先",
        source_url=_FJ_2024_PER1000,
        published=date(2025, 10, 13),
        notes=(
            "2024 figure via a Health News (健康报) article republished on "
            "the commission's official site (headline verified first-hand); "
            "measure wording 每千人口医疗机构床位数."
        ),
    ),
    # Jiangxi 2025, provincial economic bulletin: "各类医疗卫生机构（不含村
    # 卫生室）13976个" / "医院卫生院床位30.5万张"
    ResourceRecord(
        region="Jiangxi",
        metric="institutions",
        value=13_976,
        year=2025,
        source_name="Jiangxi Provincial Bureau of Statistics",
        source_title="江西省2025年国民经济和社会发展统计公报",
        source_url=_JX_2025_ECON,
        published=date(2026, 3, 27),
        notes=(
            "Economic bulletin, PRELIMINARY (初步统计数); count EXCLUDES "
            "village clinics (不含村卫生室) - a NARROWER scope than other "
            "provinces' all-institution counts. The commission publishes no "
            "bulletin (internal statistical abstract only)."
        ),
    ),
    ResourceRecord(
        region="Jiangxi",
        metric="beds",
        value=305_000,  # 30.5 万张
        year=2025,
        source_name="Jiangxi Provincial Bureau of Statistics",
        source_title="江西省2025年国民经济和社会发展统计公报",
        source_url=_JX_2025_ECON,
        published=date(2026, 3, 27),
        notes=(
            "PRELIMINARY (初步统计数); scope is HOSPITAL + township-health-"
            "center beds only (医院、卫生院床位) - not all institution beds. "
            "No per-1,000 figure in the source."
        ),
    ),
    # Shandong 2024, provincial health bulletin (PDF text extraction):
    # "全省各级各类医疗卫生机构总数达90058 个" / "床位 76.10 万张" /
    # "由 2023 年 7.30 张增加到2024 年7.55 张"
    ResourceRecord(
        region="Shandong",
        metric="institutions",
        value=90_058,
        year=2024,
        source_name="Shandong Provincial Health Commission",
        source_title="2024年山东省卫生健康事业发展统计公报",
        source_url=_SD_2024_URL,
        published=date(2025, 12, 17),
        notes="Province-wide, all levels and types (各级各类).",
    ),
    ResourceRecord(
        region="Shandong",
        metric="beds",
        value=761_000,  # 76.10 万张
        year=2024,
        source_name="Shandong Provincial Health Commission",
        source_title="2024年山东省卫生健康事业发展统计公报",
        source_url=_SD_2024_URL,
        published=date(2025, 12, 17),
        notes="万张 converted exactly (76.10万 = 761,000).",
    ),
    ResourceRecord(
        region="Shandong",
        metric="beds_per_1000",
        value=7.55,
        year=2024,
        source_name="Shandong Provincial Health Commission",
        source_title="2024年山东省卫生健康事业发展统计公报",
        source_url=_SD_2024_URL,
        published=date(2025, 12, 17),
        notes="Change endpoint 2023 (7.30) -> 2024 (7.55); 每千人口.",
    ),
    # Henan 2025, provincial economic bulletin: "年末全省共有医疗卫生机构
    # 91007个" / "医疗卫生机构床位75.15万张"
    ResourceRecord(
        region="Henan",
        metric="institutions",
        value=91_007,
        year=2025,
        source_name="Henan Provincial Bureau of Statistics",
        source_title="2025年河南省国民经济和社会发展统计公报",
        source_url=_HA_2025_ECON,
        published=date(2026, 4, 16),
        notes=(
            "Economic bulletin (the commission's own bulletin series ended "
            "2013; newer commission tables are image-only); year-end 2025; "
            "identical figures cross-verified on the provincial portal's "
            "概况 page (m.henan.gov.cn, 2026-04-16)."
        ),
    ),
    ResourceRecord(
        region="Henan",
        metric="beds",
        value=751_500,  # 75.15 万张
        year=2025,
        source_name="Henan Provincial Bureau of Statistics",
        source_title="2025年河南省国民经济和社会发展统计公报",
        source_url=_HA_2025_ECON,
        published=date(2026, 4, 16),
        notes=(
            "All-institution beds (医疗卫生机构床位); no per-1,000 figure "
            "in the source."
        ),
    ),
    # Hubei 2025, provincial economic bulletin: "年末全省共有医疗卫生机构
    # 39517家" / "医疗卫生机构床位46.06万张"
    ResourceRecord(
        region="Hubei",
        metric="institutions",
        value=39_517,
        year=2025,
        source_name="Hubei Provincial Bureau of Statistics",
        source_title="湖北省2025年国民经济和社会发展统计公报",
        source_url=_HUB_2025_ECON,
        published=date(2026, 3, 18),
        notes=(
            "Economic bulletin (the commission publishes no bulletin; its "
            "own release is an image-only table); counted in 家; year-end."
        ),
    ),
    ResourceRecord(
        region="Hubei",
        metric="beds",
        value=460_600,  # 46.06 万张
        year=2025,
        source_name="Hubei Provincial Bureau of Statistics",
        source_title="湖北省2025年国民经济和社会发展统计公报",
        source_url=_HUB_2025_ECON,
        published=date(2026, 3, 18),
        notes="No per-1,000 figure anywhere in the bulletin.",
    ),
    # Hunan 2024, provincial health bulletin (PDF text extraction):
    # "全省医疗卫生机构总数 57639 个" / "床位 523215 张" /
    # "由 2023 年 8.13 张减少为 2024 年 8.00 张"
    ResourceRecord(
        region="Hunan",
        metric="institutions",
        value=57_639,
        year=2024,
        source_name="Hunan Provincial Health Commission",
        source_title="2024年湖南省卫生健康事业发展统计公报",
        source_url=_HUN_2024_URL,
        published=date(2026, 1, 1),
        notes=(
            "Year-end 2024. Published month-precision (URL path 202601); "
            "encoded as first of month."
        ),
    ),
    ResourceRecord(
        region="Hunan",
        metric="beds",
        value=523_215,
        year=2024,
        source_name="Hunan Provincial Health Commission",
        source_title="2024年湖南省卫生健康事业发展统计公报",
        source_url=_HUN_2024_URL,
        published=date(2026, 1, 1),
        notes="Year-end 2024; published month-precision (2026-01).",
    ),
    ResourceRecord(
        region="Hunan",
        metric="beds_per_1000",
        value=8.00,
        year=2024,
        source_name="Hunan Provincial Health Commission",
        source_title="2024年湖南省卫生健康事业发展统计公报",
        source_url=_HUN_2024_URL,
        published=date(2026, 1, 1),
        notes=(
            "RESIDENT population (每千常住人口); change endpoint 2023 (8.13) "
            "-> 2024 (8.00)."
        ),
    ),
    # Guangdong 2025, commission annual analysis release: "全省医疗卫生机构
    # 68427家" / "全省医疗机构床位65.2万张" / "全省每千人口床位5.07张"
    ResourceRecord(
        region="Guangdong",
        metric="institutions",
        value=68_427,
        year=2025,
        source_name="Guangdong Provincial Health Commission",
        source_title="2025年广东省医疗卫生资源和医疗服务情况分析",
        source_url=_GD_2025_URL,
        published=date(2026, 6, 5),
        notes=(
            "The commission publishes an official annual 分析 release rather "
            "than a 统计公报; year-end 2025. Footnote 1: the hospital count "
            "EXCLUDES 妇幼保健院/专科疾病防治院 (counted under professional "
            "public-health institutions)."
        ),
    ),
    ResourceRecord(
        region="Guangdong",
        metric="beds",
        value=652_000,  # 65.2 万张
        year=2025,
        source_name="Guangdong Provincial Health Commission",
        source_title="2025年广东省医疗卫生资源和医疗服务情况分析",
        source_url=_GD_2025_URL,
        published=date(2026, 6, 5),
        notes="Scope wording 医疗机构床位; year-end 2025.",
    ),
    ResourceRecord(
        region="Guangdong",
        metric="beds_per_1000",
        value=5.07,
        year=2025,
        source_name="Guangdong Provincial Health Commission",
        source_title="2025年广东省医疗卫生资源和医疗服务情况分析",
        source_url=_GD_2025_URL,
        published=date(2026, 6, 5),
        notes=(
            "RESIDENT population (按照常住人口统计); wording 每千人口床位 "
            "(no 医疗卫生机构 qualifier)."
        ),
    ),
    # Guangxi 2024, regional health bulletin (page text): "全区医疗卫生机构
    # 共有34688家" / "床位37.73万张" / "每千人口医疗卫生机构床位数7.53张"
    ResourceRecord(
        region="Guangxi",
        metric="institutions",
        value=34_686,
        year=2024,
        source_name="Health Commission of Guangxi Zhuang Autonomous Region",
        source_title="2024年广西卫生健康事业发展统计公报",
        source_url=_GX_2024_URL,
        published=date(2025, 12, 2),
        notes="Region-wide (全区), year 2024; counted in 家.",
    ),
    ResourceRecord(
        region="Guangxi",
        metric="beds",
        value=377_300,  # 37.73 万张
        year=2024,
        source_name="Health Commission of Guangxi Zhuang Autonomous Region",
        source_title="2024年广西卫生健康事业发展统计公报",
        source_url=_GX_2024_URL,
        published=date(2025, 12, 2),
        notes="万张 converted exactly (37.73万 = 377,300).",
    ),
    ResourceRecord(
        region="Guangxi",
        metric="beds_per_1000",
        value=7.53,
        year=2024,
        source_name="Health Commission of Guangxi Zhuang Autonomous Region",
        source_title="2024年广西卫生健康事业发展统计公报",
        source_url=_GX_2024_URL,
        published=date(2025, 12, 2),
        notes="Stated with prior-year comparison (2023: 7.20 -> 2024: 7.53).",
    ),
    # Hainan 2023, provincial health bulletin (page text): "全省医疗卫生机构
    # 总数达6525个" / "床位60929张" / "2023年每千人口医疗卫生机构床位数5.84张"
    ResourceRecord(
        region="Hainan",
        metric="institutions",
        value=6_525,
        year=2023,
        source_name="Hainan Provincial Health Commission",
        source_title="海南省2023年卫生健康事业发展统计公报",
        source_url=_HAIN_2023_URL,
        published=date(2024, 7, 8),
        notes=(
            "Newest existing edition (no 2024/2025 edition published as of "
            "2026-10); year-end 2023."
        ),
    ),
    ResourceRecord(
        region="Hainan",
        metric="beds",
        value=60_929,
        year=2023,
        source_name="Hainan Provincial Health Commission",
        source_title="海南省2023年卫生健康事业发展统计公报",
        source_url=_HAIN_2023_URL,
        published=date(2024, 7, 8),
        notes="Year-end 2023.",
    ),
    ResourceRecord(
        region="Hainan",
        metric="beds_per_1000",
        value=5.84,
        year=2023,
        source_name="Hainan Provincial Health Commission",
        source_title="海南省2023年卫生健康事业发展统计公报",
        source_url=_HAIN_2023_URL,
        published=date(2024, 7, 8),
        notes=(
            "The bulletin's own footnote 12 computes this on 2021 RESIDENT "
            "population while the text cites 2023 figures - an internal "
            "inconsistency visible in the source, recorded not smoothed."
        ),
    ),
    # Chongqing 2025, municipal health bulletin (PDF text extraction):
    # "全市共有各级各类医疗卫生机构23854个" / "床位数21.26万张" (footnote 2:
    # 年底固定实有床位) / "每千人口医疗卫生机构床位数6.67张" (footnote 3:
    # 2025 常住人口)
    ResourceRecord(
        region="Chongqing",
        metric="institutions",
        value=23_854,
        year=2025,
        source_name="Chongqing Municipal Health Commission",
        source_title="2025年重庆市卫生健康事业发展统计公报",
        source_url=_CQ_2025_URL,
        published=date(2026, 8, 25),
        notes=(
            "Year-end 2025; the bulletin's Table 1 independently lists the "
            "same totals (prose/table match)."
        ),
    ),
    ResourceRecord(
        region="Chongqing",
        metric="beds",
        value=212_600,  # 21.26 万张
        year=2025,
        source_name="Chongqing Municipal Health Commission",
        source_title="2025年重庆市卫生健康事业发展统计公报",
        source_url=_CQ_2025_URL,
        published=date(2026, 8, 25),
        notes=(
            "Per footnote 2: year-end FIXED ACTUAL beds (年底固定实有床位)."
        ),
    ),
    ResourceRecord(
        region="Chongqing",
        metric="beds_per_1000",
        value=6.67,
        year=2025,
        source_name="Chongqing Municipal Health Commission",
        source_title="2025年重庆市卫生健康事业发展统计公报",
        source_url=_CQ_2025_URL,
        published=date(2026, 8, 25),
        notes=(
            "Per footnote 3: computed on 2025 RESIDENT population (常住人口) "
            "per the municipal statistics bureau."
        ),
    ),
    # Sichuan 2024, provincial health bulletin (.doc attachment, converted):
    # "全省医疗卫生机构总数74796个" / "床位71.49万张" /
    # "由2023年8.47张增加到2024年8.55张"
    ResourceRecord(
        region="Sichuan",
        metric="institutions",
        value=74_796,
        year=2024,
        source_name="Sichuan Provincial Health Commission",
        source_title="2024年四川省卫生健康事业发展统计公报",
        source_url=_SC_2024_URL,
        published=date(2026, 2, 9),
        notes=(
            "Bulletin published as a .doc attachment (converted to text via "
            "textutil); footnote 1 defines the institution scope; year-end "
            "2024."
        ),
    ),
    ResourceRecord(
        region="Sichuan",
        metric="beds",
        value=714_900,  # 71.49 万张
        year=2024,
        source_name="Sichuan Provincial Health Commission",
        source_title="2024年四川省卫生健康事业发展统计公报",
        source_url=_SC_2024_URL,
        published=date(2026, 2, 9),
        notes="万张 converted exactly (71.49万 = 714,900); year-end 2024.",
    ),
    ResourceRecord(
        region="Sichuan",
        metric="beds_per_1000",
        value=8.55,
        year=2024,
        source_name="Sichuan Provincial Health Commission",
        source_title="2024年四川省卫生健康事业发展统计公报",
        source_url=_SC_2024_URL,
        published=date(2026, 2, 9),
        notes="Change endpoint 2023 (8.47) -> 2024 (8.55); 每千人口.",
    ),
    # Guizhou 2023 bulletin: "全省医疗卫生机构总数达30722个" / "床位31.54万张" /
    # "每千人口医疗卫生机构床位数8.16张"; 2025 statistical table (卫生信息中心):
    # "机构31581个 / 床位302334张 / 每千人口床位数（常住）7.84"
    ResourceRecord(
        region="Guizhou",
        metric="institutions",
        value=30_722,
        year=2023,
        source_name="Guizhou Provincial Health Commission",
        source_title="2023年贵州省卫生健康事业发展统计公报",
        source_url=_GZ_2023_URL,
        published=date(2024, 9, 25),
        notes=(
            "The hospital category EXCLUDES maternal/child health institutions "
            "(不含妇幼保健机构, counted under professional public-health "
            "institutions). The 2023 edition is the last bulletin - the "
            "commission switched to annual statistical tables afterwards."
        ),
    ),
    ResourceRecord(
        region="Guizhou",
        metric="beds",
        value=315_400,  # 31.54 万张
        year=2023,
        source_name="Guizhou Provincial Health Commission",
        source_title="2023年贵州省卫生健康事业发展统计公报",
        source_url=_GZ_2023_URL,
        published=date(2024, 9, 25),
        notes="万张 converted exactly (31.54万 = 315,400).",
    ),
    ResourceRecord(
        region="Guizhou",
        metric="beds_per_1000",
        value=8.16,
        year=2023,
        source_name="Guizhou Provincial Health Commission",
        source_title="2023年贵州省卫生健康事业发展统计公报",
        source_url=_GZ_2023_URL,
        published=date(2024, 9, 25),
        notes="RESIDENT population basis per the bulletin's indicator note 18.",
    ),
    ResourceRecord(
        region="Guizhou",
        metric="institutions",
        value=31_581,
        year=2025,
        source_name="Guizhou Provincial Health Commission (Health Information Center)",
        source_title="2025年贵州省医疗卫生机构数量及床位数",
        source_url=_GZ_2025_TABLE,
        published=date(2026, 5, 19),
        notes=(
            "Annual statistical table (the post-bulletin publication format)."
        ),
    ),
    ResourceRecord(
        region="Guizhou",
        metric="beds",
        value=302_334,
        year=2025,
        source_name="Guizhou Provincial Health Commission (Health Information Center)",
        source_title="2025年贵州省医疗卫生机构数量及床位数",
        source_url=_GZ_2025_TABLE,
        published=date(2026, 5, 19),
        notes="Exact table figure (302,334).",
    ),
    ResourceRecord(
        region="Guizhou",
        metric="beds_per_1000",
        value=7.84,
        year=2025,
        source_name="Guizhou Provincial Health Commission (Health Information Center)",
        source_title="2025年贵州省医疗卫生机构数量及床位数",
        source_url=_GZ_2025_TABLE,
        published=date(2026, 5, 19),
        notes="RESIDENT population (常住) basis.",
    ),
    # Tibet 2025, regional health bulletin (PDF text extraction):
    # "全区医疗卫生机构总数 7436 个（含村卫生室 5220 个）" /
    # "实有床位数 22154 张" / "每千人口医疗卫生机构床位数为 5.92 张。
    # （以常住人口 374 万计算）"
    ResourceRecord(
        region="Tibet",
        metric="institutions",
        value=7_436,
        year=2025,
        source_name="Tibet Autonomous Region Health Commission",
        source_title="2025年西藏自治区卫生健康事业发展统计公报",
        source_url=_XZ_2025_URL,
        published=date(2026, 5, 14),
        notes=(
            "Region-wide (全区); includes 5,220 village clinics (stated "
            "separately). 2025 is the newest data year of any province in "
            "the registry."
        ),
    ),
    ResourceRecord(
        region="Tibet",
        metric="beds",
        value=22_154,
        year=2025,
        source_name="Tibet Autonomous Region Health Commission",
        source_title="2025年西藏自治区卫生健康事业发展统计公报",
        source_url=_XZ_2025_URL,
        published=date(2026, 5, 14),
        notes="ACTUAL beds (实有床位数).",
    ),
    ResourceRecord(
        region="Tibet",
        metric="beds_per_1000",
        value=5.92,
        year=2025,
        source_name="Tibet Autonomous Region Health Commission",
        source_title="2025年西藏自治区卫生健康事业发展统计公报",
        source_url=_XZ_2025_URL,
        published=date(2026, 5, 14),
        notes=(
            "Computed on RESIDENT population of 3.74M (常住人口 374 万, "
            "stated in the bulletin itself)."
        ),
    ),
    # Shaanxi 2025, provincial health bulletin (scanned PDF, OCR): "全省医疗
    # 卫生机构总数35131个" / Table 1 exact 床位301183张 (prose 30.12万张) /
    # "每千人口医疗卫生机构床位数由7.83张减少到7.65张"
    ResourceRecord(
        region="Shaanxi",
        metric="institutions",
        value=35_131,
        year=2025,
        source_name="Shaanxi Provincial Health Commission",
        source_title="2025年陕西省卫生健康事业发展统计公报",
        source_url=_SNX_2025_URL,
        published=date(2026, 8, 7),
        notes=(
            "SCANNED image PDF - text via macOS Vision OCR (zh-Hans), line "
            "breaks/spaces normalized, no characters changed. Cross-"
            "validated: internal arithmetic (35,426 - 295 = 35,131) and "
            "the 2024 edition's comparison column match."
        ),
    ),
    ResourceRecord(
        region="Shaanxi",
        metric="beds",
        value=301_183,
        year=2025,
        source_name="Shaanxi Provincial Health Commission",
        source_title="2025年陕西省卫生健康事业发展统计公报",
        source_url=_SNX_2025_URL,
        published=date(2026, 8, 7),
        notes=(
            "Exact Table 1 figure (301,183; prose rounds to 30.12万张); OCR-"
            "extracted, arithmetic-checked (309,715 - 8,532 = 301,183); "
            "corroborated by the 2025 economic bulletin's ~30.12万张."
        ),
    ),
    ResourceRecord(
        region="Shaanxi",
        metric="beds_per_1000",
        value=7.65,
        year=2025,
        source_name="Shaanxi Provincial Health Commission",
        source_title="2025年陕西省卫生健康事业发展统计公报",
        source_url=_SNX_2025_URL,
        published=date(2026, 8, 7),
        notes=(
            "RESIDENT population per the 2024 edition's indicator note; "
            "chain 7.75 -> 7.83 -> 7.65 consistent across the 2023/2024/"
            "2025 editions."
        ),
    ),
    # Gansu 2023, provincial health bulletin (60-page scanned PDF, OCR;
    # official origin page unreachable behind an anti-bot challenge - PDF
    # fetched from the Pingliang Municipal Health Commission mirror):
    # "全省医疗卫生机构总数25345个（含村卫生室）" / "医疗机构床位203974张" /
    # "每千人口床位8.27张"
    ResourceRecord(
        region="Gansu",
        metric="institutions",
        value=25_345,
        year=2023,
        source_name=(
            "Gansu Provincial Health Commission (PDF mirrored by Pingliang "
            "Municipal Health Commission)"
        ),
        source_title="2023年甘肃省卫生健康事业发展统计公报",
        source_url=_GS_2023_URL,
        published=date(2024, 3, 1),
        notes=(
            "Institutions INCLUDE village clinics (含村卫生室). SCANNED PDF "
            "via OCR, arithmetic-checked. The official origin page "
            "(wsjk.gansu.gov.cn) is unreachable behind a JS anti-bot "
            "challenge; 2024/2025 editions exist but could not be fetched - "
            "their figures are NOT reported. Published month-precision "
            "(cover date 2024年3月), encoded as first of month."
        ),
    ),
    ResourceRecord(
        region="Gansu",
        metric="beds",
        value=203_974,
        year=2023,
        source_name=(
            "Gansu Provincial Health Commission (PDF mirrored by Pingliang "
            "Municipal Health Commission)"
        ),
        source_title="2023年甘肃省卫生健康事业发展统计公报",
        source_url=_GS_2023_URL,
        published=date(2024, 3, 1),
        notes=(
            "Prose wording 医疗机构床位 (Table 5 titled 医疗卫生机构床位数); "
            "OCR-extracted, internal arithmetic checked (188,994 + "
            "14,980 = 203,974); the 医院床位 subcategory EXCLUDES 妇幼保健院 "
            "beds (listed separately)."
        ),
    ),
    ResourceRecord(
        region="Gansu",
        metric="beds_per_1000",
        value=8.27,
        year=2023,
        source_name=(
            "Gansu Provincial Health Commission (PDF mirrored by Pingliang "
            "Municipal Health Commission)"
        ),
        source_title="2023年甘肃省卫生健康事业发展统计公报",
        source_url=_GS_2023_URL,
        published=date(2024, 3, 1),
        notes=(
            "每千人口床位 wording (no 医疗卫生机构 qualifier), year-end 2023; "
            "OCR-extracted."
        ),
    ),
    # Qinghai 2025, provincial economic bulletin (.doc, converted via
    # textutil; the commission publishes no bulletin): "年末有医疗卫生机构
    # 6924个，床位4.72万张。其中，医院251个，床位3.95万张；…"
    ResourceRecord(
        region="Qinghai",
        metric="institutions",
        value=6_924,
        year=2025,
        source_name="Qinghai Provincial Bureau of Statistics",
        source_title="青海省2025年国民经济和社会发展统计公报",
        source_url=_QH_2025_ECON,
        published=date(2026, 3, 2),
        notes=(
            "Economic bulletin (.doc attachment); health data attributed to "
            "省卫生健康委员会 per the data-source note. The printed 8-category "
            "breakdown sums to 6,443 - a PARTIAL enumeration against the "
            "stated 6,924 total. Document dated 2026年2月28日, listed "
            "2026-03-02."
        ),
    ),
    ResourceRecord(
        region="Qinghai",
        metric="beds",
        value=47_200,  # 4.72 万张
        year=2025,
        source_name="Qinghai Provincial Bureau of Statistics",
        source_title="青海省2025年国民经济和社会发展统计公报",
        source_url=_QH_2025_ECON,
        published=date(2026, 3, 2),
        notes=(
            "万张 converted exactly (4.72万 = 47,200); no per-1,000 figure "
            "in the source."
        ),
    ),
    # Ningxia 2025, regional health bulletin (image-only page, OCR of the
    # official JPGs): "全区医疗卫生机构5136个" / "实有床位44749张" /
    # "由2024年6.07张增加到2025年6.11张"
    ResourceRecord(
        region="Ningxia",
        metric="institutions",
        value=5_136,
        year=2025,
        source_name="Ningxia Hui Autonomous Region Health Commission",
        source_title="2025年宁夏卫生健康统计公报",
        source_url=_NX_2025_URL,
        published=date(2026, 6, 25),
        notes=(
            "Page published as 21 JPGs with no text layer - figures via "
            "macOS Vision OCR of the official images (two passes, digits "
            "identical). Internal consistency checked: 215 + 4,810 + 86 + "
            "25 = 5,136."
        ),
    ),
    ResourceRecord(
        region="Ningxia",
        metric="beds",
        value=44_749,
        year=2025,
        source_name="Ningxia Hui Autonomous Region Health Commission",
        source_title="2025年宁夏卫生健康统计公报",
        source_url=_NX_2025_URL,
        published=date(2026, 6, 25),
        notes=(
            "ACTUAL beds (实有床位); OCR-extracted; cross-validated against "
            "the prior-year bulletin (2024: 49,986 institutions / 44,286 "
            "beds), exactly matching the 2025 bulletin's YoY statements."
        ),
    ),
    ResourceRecord(
        region="Ningxia",
        metric="beds_per_1000",
        value=6.11,
        year=2025,
        source_name="Ningxia Hui Autonomous Region Health Commission",
        source_title="2025年宁夏卫生健康统计公报",
        source_url=_NX_2025_URL,
        published=date(2026, 6, 25),
        notes=(
            "每千人口实有床位数 (ACTUAL-bed rate); change endpoint 2024 "
            "(6.07) -> 2025 (6.11)."
        ),
    ),
    # Xinjiang 2024, commission site reposting a 石榴云/新疆日报 report: "截至
    # 2024年底，全区医疗卫生机构总数达16739个…床位总数达17.77万张，每千人口
    # 床位数达7.85张"
    ResourceRecord(
        region="Xinjiang",
        metric="institutions",
        value=16_739,
        year=2024,
        source_name=(
            "Xinjiang Daily (石榴云, reporting regional health-commission data)"
        ),
        source_title="援疆赋能 新疆卫生健康水平全面提升",
        source_url=_XJ_2024_URL,
        published=date(2025, 7, 11),
        notes=(
            "No regional health bulletin exists online; figures released at "
            "the 2025-07-10 regional health work meeting, reported by the "
            "newspaper of record and hosted on the commission's own site "
            "(same newspaper-of-record precedent as Yunnan). As of end-2024 "
            "(截至2024年底)."
        ),
    ),
    ResourceRecord(
        region="Xinjiang",
        metric="beds",
        value=177_700,  # 17.77 万张
        year=2024,
        source_name=(
            "Xinjiang Daily (石榴云, reporting regional health-commission data)"
        ),
        source_title="援疆赋能 新疆卫生健康水平全面提升",
        source_url=_XJ_2024_URL,
        published=date(2025, 7, 11),
        notes=(
            "Bed type (实有/编制) NOT specified in the source. SCOPE "
            "caveat: the implied population denominator (~22.64M) suggests "
            "figures EXCLUDING the Xinjiang Production and Construction "
            "Corps (兵团); whether 兵团 is included cannot be determined from "
            "the source - the dual-track structure is flagged, not smoothed."
        ),
    ),
    ResourceRecord(
        region="Xinjiang",
        metric="beds_per_1000",
        value=7.85,
        year=2024,
        source_name=(
            "Xinjiang Daily (石榴云, reporting regional health-commission data)"
        ),
        source_title="援疆赋能 新疆卫生健康水平全面提升",
        source_url=_XJ_2024_URL,
        published=date(2025, 7, 11),
        notes=(
            "每千人口床位数 with the same 兵团 scope caveat as the "
            "institutions/beds records."
        ),
    ),
)


def recorded_regions(records: tuple[ResourceRecord, ...]) -> list[str]:
    """Regions with at least one verified record (national excluded)."""
    return sorted({r.region for r in records if r.region in PROVINCES})


def unrecorded_provinces(records: tuple[ResourceRecord, ...]) -> list[str]:
    """Provinces with NO verified record - named missingness.

    The registry records only what was directly verified; every other
    province is explicitly listed here rather than imputed, estimated,
    or silently omitted.
    """
    recorded = set(recorded_regions(records))
    return [p for p in PROVINCES if p not in recorded]


@dataclass(frozen=True)
class ExposureReport:
    """What one episode window suspends, per the verified records.

    ``record_year`` is carried alongside the figures so the report never
    implies the exposure numbers are at-episode-year values.
    """

    episode_id: str
    region: str
    institutions: int | None
    beds: int | None
    record_year: int | None
    record_sources: tuple[str, ...]


def exposure_report(
    episode: Episode,
    records: tuple[ResourceRecord, ...] = VERIFIED_RECORDS,
) -> ExposureReport:
    """Resource exposure of an episode: the latest verified records for
    the episode's region, explicitly dated (record year vs episode year).

    The episode's region is matched against provincial records only; a
    region with no verified records returns None values with the sources
    that were searched - missingness named, never guessed.
    """
    matching = [r for r in records if r.region == episode.region]
    latest_year = max((r.year for r in matching), default=None)
    latest = [r for r in matching if r.year == latest_year] if latest_year else []

    def metric_value(metric: str) -> int | None:
        for record in latest:
            if record.metric == metric:
                return int(record.value)
        return None

    sources = tuple(
        sorted({f"{r.source_name} ({r.source_title}, {r.year})" for r in latest})
    )
    return ExposureReport(
        episode_id=episode.episode_id,
        region=episode.region,
        institutions=metric_value("institutions"),
        beds=metric_value("beds"),
        record_year=latest_year,
        record_sources=sources,
    )


__all__ = [
    "CASE_STUDY_COUNTRIES",
    "PROVINCES",
    "PROVINCIAL_METRICS",
    "RECORD_EVIDENCE_LABEL",
    "VERIFIED_RECORDS",
    "ExposureReport",
    "ResourceRecord",
    "exposure_report",
    "recorded_regions",
    "unrecorded_provinces",
]
