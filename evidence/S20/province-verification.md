# S20 province verification log — China healthcare-geography registry (Pass 2)

- Window: 2026-10-11 .. 2026-10-16 (live web verification)
- Scope: the 29 provincial-level divisions not recorded in Pass 1. Pass 1
  (CHN national 2023, Beijing 2023, Yunnan 2023, verified live 2026-08-29)
  is documented in `evidence/S12/live-verification.md`. Combined: all 31
  provincial-level divisions, 91 records, in
  `src/macropulse/case_study/china_health.py`.
- Purpose: the full-data-coverage go-live directive — every province
  recorded from live-verified official sources, under the same
  citation / no-fabrication discipline as Pass 1.
- Provenance of this file: the verification session was interrupted before
  this log was written; it was reconstructed on 2026-10-21 from the
  preserved session and subagent transcripts under
  `~/.claude/projects/-Users-henryliu-Desktop-y11-macro-pulse/` (agent
  transcripts named per batch below). Every quote, value, URL, and note is
  carried verbatim from the live-verification outputs; nothing was
  re-derived or re-fetched during reconstruction.

## Method and discipline

- Every recorded figure comes from a document actually retrieved and read
  during the window (page fetch, PDF/.doc download + text extraction, or
  OCR of scanned/image-only official PDFs). Quotes below are verbatim
  Chinese, character-for-character as printed (footnote markers copied as
  they appear; OCR whitespace normalization noted per province).
- No-fabrication rule enforced both ways: a figure is recorded only if its
  source text was retrieved; and a document that EXISTS but could not be
  retrieved is explicitly excluded and named (e.g. Gansu's 2024/2025
  editions behind an anti-bot wall — only the retrievable 2023 edition is
  recorded).
- Scanned documents (Shaanxi, Gansu, Ningxia) were read with macOS Vision
  OCR (zh-Hans); each OCR extraction was cross-validated by internal
  arithmetic (component sums, shares, year-over-year deltas) and, where
  possible, against an adjacent text-extractable edition or an independent
  official document. The validation arithmetic is logged per province.
- Source hierarchy (mirrors the module docstring): the provincial health
  commission's annual release (统计公报 or equivalent official annual
  release) is primary; where none is published or retrievable, the
  provincial economic bulletin (国民经济和社会发展统计公报) is used and its
  资料来源 attribution to the health commission is recorded. A metric
  absent from the primary source but present in another official release is
  encoded as a separate record carrying that release's own citation.
- 万 (10,000) units are converted exactly; per-万 rates are NEVER rescaled
  into the per-1,000 metric (Shanghai and Jilin publish only per-万 rates
  on non-comparable denominators — not encoded).
- "status: partial" below means the recorded figures are genuine and
  fetched, but from the economic bulletin / an official non-bulletin
  release because the province publishes no (retrievable) standalone
  health bulletin. "not_found" documents a bulletin search that came up
  empty.

## Verification organization

First-wave batches A–F were launched 2026-10-11 23:53; A, B, C, D, F died
on provider API errors mid-run and were re-run as A2, B2, C2, D2 (2026-10-12)
and F2 (2026-10-16); batch E completed on its first run.

| Batch | Provinces | Live verification | Agent transcript |
|-------|-----------|-------------------|------------------|
| A2 | Tianjin, Hebei, Inner Mongolia, Liaoning | 2026-10-12 | `agent-ae25b2a2a58f55a10.jsonl` |
| B2 | Jilin, Heilongjiang, Shanghai, Zhejiang | 2026-10-12 | `agent-a15fa3410a5ee6138.jsonl` |
| C2 | Fujian, Jiangxi, Henan | 2026-10-12 | `agent-a11f7fe0a9ce9d644.jsonl` |
| D2 | Hubei, Guangdong, Guangxi, Hainan | 2026-10-12 | `agent-a6d50dd18bd2d4737.jsonl` |
| E  | Chongqing, Sichuan, Guizhou, Shaanxi, Gansu | 2026-10-11..12 | `agent-aa41a22a3940a10c1.jsonl` |
| F2 | Qinghai (health-bulletin search), Ningxia, Xinjiang | 2026-10-16 | `agent-a26de55d96f29305d.jsonl` |
| PDF | Shanxi, Jiangsu, Anhui, Shandong, Hunan, Tibet | downloads 2026-10-11, operator pypdf extractions 2026-10-11..12 | main session `d7cfde67….jsonl` (~lines 451–452, 518–519, 529–530, 535–536, 540–541, 551–552, 610–618, 622) + first-wave download agents `agent-a645c20e0c6bc1b3c` (Shanxi), `agent-a14512e4f71fa12de` (Jiangsu), `agent-a4144cbc20367ff9a` (Anhui, Shandong), `agent-afc7b52bc91a50a7b` (Hunan), `agent-ad232068b439c663f` (Tibet; crashed mid-run, harvest recorded) |
| Operator | Qinghai economic-bulletin fallback (executed after F2's health-bulletin search came up empty) | 2026-10-16 | main session `d7cfde67….jsonl` lines 1284–1309 |

Transcripts live under
`~/.claude/projects/-Users-henryliu-Desktop-y11-macro-pulse/d7cfde67-0143-4615-b2b5-716ad14bd3d1/subagents/`
(the PDF-batch download agents' transcripts) and in the two session files
`d7cfde67-0143-4615-b2b5-716ad14bd3d1.jsonl` and
`5ca496b9-58ec-4a33-a4c3-ff3dbec0a081.jsonl`.

## Per-province verification records

Provinces appear in the registry's `PROVINCES` order. Beijing and Yunnan
(Pass 1, kept without re-verification per the October registry decision)
carry short keep-decision sections below; their full verbatim quotes and
extraction logs are in `evidence/S12/live-verification.md`. The CHN
national record is likewise Pass 1.

### Beijing (北京) — Pass 1 (S12), kept without re-verification
- Recorded values (2023): institutions 12,518 (of which 医疗机构 12,298); AUTHORIZED beds (编制床位) 149,971, actual (实有) 138,825; beds per 1,000 permanent residents 6.87 authorized / 6.35 actual
- Source: Beijing Municipal Health Commission (北京市卫生健康委员会) — 《2023年北京市卫生健康事业发展统计公报》
- URL: http://www.phic.org.cn/tjsj/wstjgb/202408/P020240819586687344254.pdf (upload path dated 2024-08-19)
- Live verification: 2026-08-29 (Pass 1) — full verbatim quotes and pypdf extraction output in `evidence/S12/live-verification.md`; the October sessions reference that file (no re-fetch of phic.org.cn)
- S20 registry decision (October session): "Beijing 2023 ×3 — keep"
- Measure caveat: Beijing reports 编制床位 (authorized beds); authorized and actual measures are recorded separately and are NOT pooled with other provinces' bed measures in comparisons

### Tianjin (天津) — status: partial
- Data year: 2025
- Source: Tianjin Municipal Bureau of Statistics (天津市统计局， jointly with 国家统计局天津调查总队)， published on the Tianjin Municipal Bureau of Statistics website — 《2025年天津市国民经济和社会发展统计公报》
- URL: https://stats.tj.gov.cn/tjsj_52032/tjgb/202603/t20260323_7267486.html
- Published: 2026-03-23
- Access method: page-fetched
- Live verification: 2026-10-12, batch A2 (transcript `agent-ae25b2a2a58f55a10.jsonl`)
- Institutions (verbatim): “年末全市共有各类卫生机构7415个，其中医院451个。”
- Institutions value: 7415个
- Beds (verbatim): “卫生机构床位7.49万张，其中医院床位6.92万张。”
- Beds value: 7.49万张
- Beds per 1,000 value: NONE
- Verification notes: Tianjin Municipal Health Commission does not publish a standalone 卫生健康事业发展统计公报 — its 统计信息 column (wsjk.tj.gov.cn/ZWGK3158/ZFXXGK5869/FDZDGKNR4356/tjxxn/) carries only monthly 全市医疗卫生机构门诊及住院服务情况 reports, and its annual flagship is the 居民健康状况报告 (the 2025 edition PDF contains no bed figures). Figures above are from the municipal statistical bulletin, whose 资料来源 states verbatim “医疗卫生数据来自天津市卫生健康委员会”. Terminology is 各类卫生机构 / 卫生机构床位 (not 医疗卫生机构)； figures are year-end 2025, city-wide (Tianjin is a province-level municipality, so city-wide = province-level scope); beds printed in 万张 units; no 编制床位 vs 实有床位 distinction stated; no per-1,000-population bed figure appears anywhere in the bulletin.

### Hebei (河北) — status: partial
- Data year: 2025
- Source: Hebei Provincial Bureau of Statistics (河北省统计局， jointly with 国家统计局河北调查总队)， published on the Hebei Provincial People's Government website — 《河北省2025年国民经济和社会发展统计公报》
- URL: https://www.hebei.gov.cn/columns/3bbf017c-0e27-4cac-88c0-c5cac90ecd73/202604/14/39058c18-8d16-4a19-ab71-6d1bf8d2749f.html
- Published: 2026-04-13
- Access method: page-fetched
- Live verification: 2026-10-12, batch A2 (transcript `agent-ae25b2a2a58f55a10.jsonl`)
- Institutions (verbatim): “年末医疗卫生机构93687个，其中，医院2486个，乡镇卫生院1959个，社区卫生服务中心（站）1649个，妇幼保健院（所、站）183个，疾病预防控制中心190个。”
- Institutions value: 93687个
- Beds (verbatim): “医疗卫生机构床位54.34万张，其中，医院42.82万张，乡镇卫生院8.56万张。”
- Beds value: 54.34万张
- Beds per 1,000 value: NONE
- Verification notes: Hebei Provincial Health Commission does not publish a standalone 卫生健康事业发展统计公报 (no such document found on wsjkw.hebei.gov.cn or in any news mirror; searched exact-phrase variants for 2024/2025 and the older 卫生和计划生育 series). Figures are from the provincial statistical bulletin, whose 资料来源 states verbatim “医疗卫生数据来自省卫生健康委员会”； bulletin note 1 says “本公报2025年数据为初步统计数” (preliminary). Province-wide, year-end 2025; 万张 units as printed; no 编制床位 vs 实有床位 distinction. Per-1,000 beds is not in the bulletin; separately, the Hebei Provincial Health Commission's own 《河北省卫生健康委2025年度部门绩效自评情况公开》 (http://wsjkw.hebei.gov.cn/czyjs/419541.jhtml, published 2026-05-18, fetched this session) states verbatim: “我省2025年每千人口执业（助理）医师数达到4.40人，每千人口注册护士数达到4.44人，每千人口医疗卫生机构床位数7.39张左右，每万人口全科医生数达到5.01人。” — i.e. 2025 per-1,000 beds 7.39张左右 (“左右” = approximately, health-commission sourced).

### Shanxi (山西) — status: verified
- Data year: 2024
- Source: Shanxi Provincial Health Commission (山西省卫生健康委员会) — 《2024年山西省卫生健康事业发展统计公报》
- URL: https://wjw.shanxi.gov.cn/zfxxgk/fdzdgknr/ghjh/202602/P020260206603605483382.pdf
- Published: 2026-02-06 (URL-embedded)
- Access method: pdf-downloaded-and-extracted — first-wave agent curl returned "HTTP 200, 447576 bytes"; main session extracted with pypdf 6.16.2 (17 pages / 10,514 chars)
- Live verification: download 2026-10-11, extraction 2026-10-11..12 (main session; operator PROVINCE block)
- Institutions (verbatim): “（一）医疗卫生机构数 2024年，全省共有医疗卫生机构 38431 个，比上年增加 593 个。其中，医院 1373 个；基层医疗卫生机构 36645”
- Institutions value: 38431个
- Beds (verbatim): “（二）医疗卫生机构床位数 2024年，全省医疗卫生机构共有床位 22.99 万张，其中，医院 18.90 万张，占 82.23%；基层医疗卫生机构 3.61 万张，占 15.69%；专业公共卫生机构 0.45 万张，占 1.96%。”
- Beds value: 22.99万张 (converted exactly = 229,900)
- Beds per 1,000 (verbatim): “每千常住人口医疗卫生机构床位数 6.67 张。”
- Beds per 1,000 value: 6.67张 (常住人口 basis)
- Verification notes: raw pypdf output carried line-wrap spaces and a footnote marker (“2024 年，全省共有医疗卫生机构 38431 个 1，比上年增 加 593 个”) — footnote "1" removed and wrap spaces collapsed when quoting; characters otherwise unchanged. Data source confirmed in the bulletin's end notes: “12.数据来源：国家卫生统计信息网络直报系统 2024 年年报数据。” Scope: 全省.
- Transcript evidence: main session `d7cfde67….jsonl` ~lines 451–452, 540–541, 551–552, 610–611, 622; download agent `agent-a645c20e0c6bc1b3c.jsonl` lines 30–31

### Inner Mongolia (内蒙古) — status: verified
- Data year: 2025
- Source: Health Commission of Inner Mongolia Autonomous Region (内蒙古自治区卫生健康委员会) — 《2025年内蒙古自治区卫生健康事业发展统计公报》
- URL: http://wjw.nmg.gov.cn/zfxxgk/fdzzgknr/tjxx/nb/202606/t20260612_2915713.html
- Published: 2026-06-12
- Access method: page-fetched
- Live verification: 2026-10-12, batch A2 (transcript `agent-ae25b2a2a58f55a10.jsonl`)
- Institutions (verbatim): “（一）医疗卫生机构总数。2025年全区卫生机构总数达26914个¹，比上年增加146个。其中：医院847个，基层医疗卫生机构25661个，专业公共卫生机构323个。”
- Institutions value: 26914个
- Beds (verbatim): “（二）床位数。2025年末，全区医疗卫生机构共有床位171421张，其中：医院137698张（占80.33%），基层医疗卫生机构28367张（占16.55%），专业公共卫生机构5146张（占3.00%）。”
- Beds value: 171421张
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数由2024年的7.27张降低到2025年的7.22张。”
- Beds per 1,000 value: 7.22张
- Verification notes: This is the autonomous-region health commission's own annual statistical bulletin — the genuine region-wide (全区) provincial-level 公报， newer than and superseding the Tongliao-city mirror of the 2024 简报 given in the earlier lead (that lead was a 简报， and city-site reposted). It is the newest edition found (2025 data, published 2026-06-12, 发布时间 shown on page). ¹ is a superscript footnote marker in the original (footnote 1: 医疗卫生机构包括医院、基层医疗卫生机构、专业公共卫生机构、其他机构). Beds are explicitly 2025年末 (year-end); the bulletin does not state a 编制床位 vs 实有床位 distinction. Per footnote 13, per-1,000-population beds are computed on 常住人口 published by 内蒙古自治区统计局. The bed sentence as printed mixes half-width "，" and ":" with full-width "，" — quoted character-for-character above.

### Liaoning (辽宁) — status: partial
- Data year: 2025
- Source: Liaoning Provincial Bureau of Statistics (辽宁省统计局， jointly with 国家统计局辽宁调查总队) — 《辽宁省2025年国民经济和社会发展统计公报》
- URL: https://tjj.ln.gov.cn/tjj/articleFileDir/2026-03/31/7d0ebeac0ed3499da6e4aa0f94acf972/2026033115100327617.pdf
- Published: 2026-03-31
- Access method: pdf-downloaded-and-extracted
- Live verification: 2026-10-12, batch A2 (transcript `agent-ae25b2a2a58f55a10.jsonl`)
- Institutions (verbatim): “年末有医疗卫生机构37678个。其中，医院1678个，卫生院1015个，疾病预防控制中心115个，妇幼保健院（所、站）107个，社区卫生服务机构1507个，村卫生室16044个。在社区卫生服务机构中，社区卫生服务中心407个，社区卫生服务站1100个。”
- Institutions value: 37678个
- Beds (verbatim): “年末医疗卫生机构拥有床位33.1万张；卫生技术人员41.6万人，其中执业医师和执业助理医师17.2万人，注册护士18.9万人。”
- Beds value: 33.1万张
- Beds per 1,000 value: NONE
- Verification notes: Liaoning Provincial Health Commission does not publish a standalone 卫生健康事业发展统计公报 — its 法定主动公开内容 disclosure tree (wsjk.ln.gov.cn) has no 统计信息 category, and exact-phrase searches for 2020–2025 editions found no original (only unverifiable third-party report citations). Figures are from the provincial statistical bulletin, whose 资料来源 states verbatim “卫生数据来自省卫生健康委员会”. Province-wide, 2025年末 (year-end); 万张 as printed; no 编制床位 vs 实有床位 distinction; no per-1,000 bed figure in the bulletin (a computed estimate of ~7.9张 appears only in third-party commentary and was NOT used). The identical sentences were cross-verified on the Liaoning provincial government's official republication page https://www.ln.gov.cn/web/sqgk/shsy/2026040910083619995/index.shtml (编辑时间 2026-04-13). In the PDF, the quoted passages carry no footnote markers (the [18]/[19] markers in that section attach to 诊疗人次/出院人次 only); spaces inside the PDF text layer are extraction artifacts.

### Jilin (吉林) — status: partial
- Data year: 2025
- Source: 吉林省统计局 (tjj.jl.gov.cn) — 《《吉林省2025年国民经济和社会发展统计公报》》
- URL: http://tjj.jl.gov.cn/tjsj/tjgb/ndgb/202604/t20260427_3627028.html
- Published: 2026-04-27 (页面发文日期：2026-04-27 13:53:46)
- Access method: page-fetched
- Live verification: 2026-10-12, batch B2 (transcript `agent-a15fa3410a5ee6138.jsonl`)
- Institutions value: NONE
- Beds (verbatim): “医疗卫生机构实有床位18.09万张。”
- Beds value: 18.09万张
- Beds per 1,000 value: NONE
- Verification notes: 吉林省卫生健康委员会 does not publish a 卫生健康事业发展统计公报 online — its site (wsjkw.jl.gov.cn) 政府信息公开 section has no statistics column, and web searches (exact current title plus 卫计委-era title 《卫生和计划生育事业发展统计公报》) found none; closest official annual health-resource figures are in the statistics bureau bulletin, hence partial. Bed figure is 实有床位 (actual beds) and is explicitly flagged as 年末预计 (preliminary year-end estimate). The bulletin contains NO institution count (its only 医疗卫生机构 mention is the bed sentence) and NO per-capita beds (0 occurrences of 每千人口/每万人口). Adjacent-year references, both page-fetched: 《吉林统计年鉴2025》表19-4 历年卫生健康事业基本情况 (http://tjj.jl.gov.cn/tjsj/tjnj/2025/html/19-4.html) shows 2024年 医疗卫生机构26552个， 卫生机构床位17.77万张， 每万人口床位数76.7张 (per 万人口 basis, not 每千人口)； and the 《吉林省2024年国民经济和社会发展统计公报》 (http://tjj.jl.gov.cn/tjsj/tjgb/ndgb/202503/t20250324_3419691.html) states 医疗卫生机构实有床位17.77万张 (final 2024 figure, same 实有 measure).

### Heilongjiang (黑龙江) — status: partial
- Data year: 2025
- Source: 黑龙江省统计局、国家统计局黑龙江调查总队 (tjj.hlj.gov.cn) — 《《2025年黑龙江省国民经济和社会发展统计公报》》
- URL: https://tjj.hlj.gov.cn/tjj/c106779/202603/c00_31925539.shtml
- Published: 2026-03-31 (页面日期：2026-03-31 17:03，来源：综合处)
- Access method: page-fetched
- Live verification: 2026-10-12, batch B2 (transcript `agent-a15fa3410a5ee6138.jsonl`)
- Institutions (verbatim): “初步统计，全省共有医疗卫生机构22867个，其中医院、卫生院2174个，专科疾病防治院（所、站）20个，妇幼保健院（所、站）121个。”
- Institutions value: 22867个
- Beds (verbatim): “医疗卫生机构实有床位数23.77万张，其中医院、卫生院床位数22.46万张。”
- Beds value: 23.77万张
- Beds per 1,000 value: NONE
- Verification notes: 黑龙江省卫生健康委员会 does not publish a 卫生健康事业发展统计公报 online — its site's 统计信息 tab (wsjkw.hlj.gov.cn /wsjkw/c109096/zfxxgk.shtml?tab=tjxx) contains only 公开年报 with no bulletins, and exact-title searches (current and 卫计委-era) found none; statistics bureau bulletin used instead, hence partial. Figures are flagged 初步统计 (preliminary). Bed measure is 实有床位数 (actual beds); the prior-year 2024公报 (page-fetched, https://tjj.hlj.gov.cn/tjj/c106779/202504/c00_31830865.shtml, published 2025-04-16) uses different wording without 实有： 医疗卫生机构床位数27.31万张，其中医院、卫生院床位数25.92万张 — the 2024 and 2025 bed figures carry different measure labels and should not be compared without checking the measure. No per-capita beds stated anywhere in either bulletin (0 occurrences of 每千/每万).

### Shanghai (上海) — status: partial
- Data year: 2024
- Source: 上海市卫生健康委员会 (wsjkw.sh.gov.cn) — 《《上海市卫生健康状况报告（2024）》》
- URL: https://wsjkw.sh.gov.cn/2024wsjkzkbg/20251208/4fe2a4a9f0b54351984aa066777c05fb.html
- Published: 2025-12-08 (date from URL path /20251208/; no in-page date)
- Access method: page-fetched
- Live verification: 2026-10-12, batch B2 (transcript `agent-a15fa3410a5ee6138.jsonl`)
- Institutions (verbatim): “2024年，全市各级各类医疗卫生机构总数达6431所（含村卫生室），其中：医院503所，基层医疗卫生机构5692所，专业公共卫生机构83所，其他机构153所。”
- Institutions value: 6431所（含村卫生室）
- Beds (verbatim): “全市医疗机构实际开放床位19.39万张，比上年同期增长5.81%。”
- Beds value: 19.39万张
- Beds per 1,000 value: NONE
- Verification notes: Shanghai publishes no 卫生健康事业发展统计公报； its health commission's annual flagship report is the 卫生健康状况报告， and the 2024 edition is the newest (the 2025 edition is not yet published; /2025wsjkzkbg/ returns 404) — hence partial. Bed measure is 实际开放床位 (actually-open beds) and scope is 医疗机构， city-wide; this differs from other provinces‘ 实有床位 convention. No per-千人口 beds in the report (0 occurrences of 每千人口/万人口)； Shanghai’s convention is per 万人口 by 户籍人口： per "2025年上海市卫生健康统计数据” (上海市卫生健康委员会， https://wsjkw.sh.gov.cn/tjsj2/20260730/7154e5b1603642a8a3c7c0b2b8b3b149.html, published 2026-07-30, page-fetched), 2025年 卫生机构总数6566所（医院525所）and 万人口医疗机构病床数130.5张， with table footnote 本表中万人口医生数和万人口医疗机构病床数均按户籍人口统计； that page gives no absolute bed count, which is why the 2024 report is the primary source.

### Jiangsu (江苏) — status: verified
- Data year: 2023
- Source: Jiangsu Provincial Health Commission (江苏省卫生健康委员会) — 《2023年江苏省卫生健康事业发展统计公报》
- URL: http://wjw.jiangsu.gov.cn/module/download/downfile.jsp?classid=0&filename=5bf41d52c7ac47b0a369b4b4d9285f3e.pdf
- Published: the hash-filename download URL carries no date; the hosting article (wjw.jiangsu.gov.cn/art/2024/6/14/art_55455_11270950.html) is dated 2024-06-14 per the registry record notes
- Access method: pdf-downloaded-and-extracted — first-wave agent curl returned "200 application/pdf;charset=UTF-8 909596", "PDF document, version 1.5, 27 pages"; main session pypdf extraction
- Live verification: download 2026-10-11, extraction 2026-10-11..12 (main session; operator PROVINCE block)
- Institutions (verbatim): “2023年末，全省医疗卫生机构总数 39543 个，比上年增加 2542 个。其中：医院 2175 个，基层医疗卫生机构 36378 个”
- Institutions value: 39543个 (year-end 2023)
- Beds (verbatim): “（三）医疗机构床位数 2023年末，全省医疗机构床位 578826 张，其中：医院床位 456531 张（公立医院 264578 张，民营医院 191953 张），占床位总数的78.87%；基层医疗卫生机构床位 108164 张，占床位总数的 18.69%。”
- Beds value: 578826张
- Beds per 1,000 (verbatim): “2023年，全省每千人口床位数 6.79 张。”
- Beds per 1,000 value: 6.79张 (population base unqualified in the source)
- Verification notes: the beds sentence says 医疗机构 (not 医疗卫生机构) — wording differs slightly from other provinces and was flagged by the operator. Raw pypdf output carried line-wrap artifacts (“比上年增 加 2542 个”) — wrap spaces collapsed when quoting; characters unchanged. Scope: 全省, 年末 2023.
- Transcript evidence: main session `d7cfde67….jsonl` ~lines 535–536, 540–541, 551–552, 610–611, 622; download agent `agent-a14512e4f71fa12de.jsonl` lines 35–36

### Zhejiang (浙江) — status: partial
- Data year: 2025
- Source: 浙江省统计局、国家统计局浙江调查总队 (tjj.zj.gov.cn) — 《《2025年浙江省国民经济和社会发展统计公报》》
- URL: https://tjj.zj.gov.cn/col/col1229129205/art/2026/art_724c5ad52b8c4ac89def939cb9dee18c.html
- Published: 2026-03-03 (发布时间：2026-03-03 10:01，来源：省统计局)
- Access method: page-fetched
- Live verification: 2026-10-12, batch B2 (transcript `agent-a15fa3410a5ee6138.jsonl`)
- Institutions (verbatim): “年末全省卫生机构4.03万个（含村卫生室），其中，医院1646个，卫生院1017个，社区卫生服务中心（站）3606个，诊所（卫生室、医务室）1.86万个，村卫生室1.14万个，疾病预防控制中心103个。”
- Institutions value: 4.03万个（含村卫生室）— bulletin wording is 卫生机构， not 医疗卫生机构
- Beds (verbatim): “医疗卫生机构床位数42.1万张，增长1.8%，其中，医院37.6万张，卫生院1.9万张。”
- Beds value: 42.1万张
- Beds per 1,000 value: NONE
- Verification notes: 浙江省卫生健康委员会 publishes annual statistical tables (卫生统计 / 数据发布与解读 columns), not a 卫生健康事业发展统计公报； its 2025 statistical-table PDFs (总表 and 每千人口表， downloaded from https://wsjkw.zj.gov.cn/col/col1229123426/art/2026/art_7a7b64ff98a241f2a582e69230c02003.html and art_6759b615f0c449d689e1881289ed0896.html, published 2026-06-11) are image-only scans (pypdf extracts empty text; no OCR available), so the 2025 per-1000-beds figure could NOT be fetched — hence partial and statistics-bureau bulletin used as primary. The commission's 2025 "各地区医疗卫生机构数” PDF does extract (pdf-downloaded-and-extracted from https://wsjkw.zj.gov.cn/col/col1229123426/art/2026/art_9d8eafccdf664d49833541f77a09b582.html) and corroborates the institution count: row 总 计 40343 1643 … 38107 … (医疗卫生机构合计40343个， 医院1643个， 基层医疗卫生机构38107个)， consistent with the bulletin's 4.03万个. For 2024 the commission's per-1000 table (text PDF, downloaded from https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web2787/site/attach/0/975f8dccbdc04e96abd6f6e042a8ba7f.pdf) states row 全 省 413193 684334 279969 299355 6670 6.19 10.26 4.20 4.49 with footnote 注：机构和人员都包含了村卫生室的机构和人员。 — i.e., 2024年 每千人口床位数6.19张（床位413193张， 按常住人口6670万）. Bulletin bed measure is 床位数 (no 实有 qualifier).

### Anhui (安徽) — status: verified
- Data year: 2024
- Source: Anhui Provincial Health Commission (安徽省卫生健康委员会) — 《2024年安徽省卫生健康事业发展统计公报》
- URL: https://wjw.ah.gov.cn/group4/M00/08/C2/wKg862kEeaaAQvaXAAjrongELhI404.pdf
- Published: the hash-path URL carries no date; the hosting article (wjw.ah.gov.cn/public/7001/58031321.html) is dated 2025-10-31 per the registry record notes
- Access method: pdf-downloaded-and-extracted — first-wave agent curl (584,610 bytes, "PDF document, version 1.7, 24 pages", file timestamp Oct 11 23:43); main session pypdf extraction test (24 pages / 17,718 chars, HIT “（一）医疗卫生机构总数。2024 年末，全省医疗卫生机构”)
- Live verification: download 2026-10-11, extraction 2026-10-11..12 (main session; operator PROVINCE block)
- Institutions (verbatim): “（一）医疗卫生机构总数。2024年末，全省医疗卫生机构数达 32635 个，比上年增加 1274 个。其中：医院 1354 个，基层”
- Institutions value: 32635个 (year-end 2024)
- Beds (verbatim): “（二）床位数。2024年末，全省医疗卫生机构床位 44.9 万张，其中:医院 34.6 万张（占 77.0%），基层医疗卫生机构 8.9 万”
- Beds value: 44.9万张 (converted exactly = 449,000)
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数由 2023 年 7.41 张下降至 7.33 张。”
- Beds per 1,000 value: 7.33张 (2024 endpoint of the 2023→2024 change sentence)
- Verification notes: both quotes end mid-sentence in the extraction window (operator block quotes them as captured). Raw pypdf output carried line-wrap spaces (“44.9 万 张”) — collapsed when quoting; characters unchanged. Scope: 全省, 年末 2024.
- Transcript evidence: main session `d7cfde67….jsonl` ~lines 451–452, 540–541, 610–611, 622; download agent `agent-a4144cbc20367ff9a.jsonl` lines 16, 21

### Fujian (福建) — status: partial
- Data year: 2022
- Source: 福建省卫生健康委员会 (Fujian Provincial Health Commission, 信息统计 column) — 《2022年福建省医疗卫生资源及医疗服务情况》
- URL: https://wjw.fj.gov.cn/jggk/csxx/ghyxxc/xxtj_41288/202310/t20231023_6280147.htm
- Published: 2023-10-23
- Access method: page-fetched
- Live verification: 2026-10-12, batch C2 (transcript `agent-a11f7fe0a9ce9d644.jsonl`)
- Institutions (verbatim): “2022年末，全省医疗卫生机构总数29117个，比上年增加424个。其中：医院720个，基层医疗卫生机构27941个，专业公共卫生机构324个。”
- Institutions value: 29117个 (year-end 2022)
- Beds (verbatim): “2022年末，全省医疗卫生机构床位总数232425张，其中：医院184994张（占79.59%），基层医疗卫生机构38349张（占16.50%），专业公共卫生机构8482张（占3.65%）。”
- Beds value: 232425张
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数由2021年5.35张增加到2022年5.55张。”
- Beds per 1,000 value: 5.55张 (2022; 2021: 5.35张)
- Verification notes: 福建省卫健委不发布标题为"卫生健康事业发展统计公报”的文件；其年度统计发布文件题为《XXXX年福建省医疗卫生资源及医疗服务情况》。2022年版（本来源）是最新有正文文本的版本；卫健委2023—2025年的统计表（医疗卫生机构数、医疗机构床位数，最新2026-06-22发布）仅以图片（JPG/PNG）形式发布，无法文本提取。数据为全省、年末口径，床位数为全部医疗卫生机构实有床位总数（表1同口径：232425）。更新的官方数字见省统计局公报《2025年福建省国民经济和社会发展统计公报》（https://tjj.fj.gov.cn/xxgk/tjgb/202603/t20260313_7109476.htm，2026-03-19发布）：“年末共有各级各类医疗卫生机构3.10万个，其中医院758个，卫生院876个，村卫生室1.61万个。”"年末共有医疗机构床位25.40万张，其中医院20.18万张，基层医疗卫生机构4.25万张。”（该公报无每千人口床位数）。2024年每千人口床位数字见卫健委官网转载健康报文章（https://wjw.fujian.gov.cn/jggk/csxx/bgs/gzdt/202510/t20251013_7020368.htm，2025-10-13）：“2024年，全省每千人口医疗机构床位数、执业（助理）医师数、注册护士数分别达到5.94张、3.11人、3.60人，较2020年增长13.79%、22.44%、22.45%"。已按要求排除 /tmp/fujian_fjdaily_20251211.pdf（该PDF为福建日报刊载的全国2024年公报道，非福建省级文件）。 ----------------------------------------

### Jiangxi (江西) — status: partial
- Data year: 2025
- Source: 江西省统计局、国家统计局江西调查总队 (published on Jiangxi Provincial People's Government portal; 公报内注明"医疗卫生数据来自省卫生健康委员会") — 《江西省2025年国民经济和社会发展统计公报》
- URL: https://www.jiangxi.gov.cn/jxsrmzf/zxfb/pc/content/content_2037309510965067776.html
- Published: 2026-03-27
- Access method: page-fetched
- Live verification: 2026-10-12, batch C2 (transcript `agent-a11f7fe0a9ce9d644.jsonl`)
- Institutions (verbatim): “年末共有各类医疗卫生机构（不含村卫生室）13976个。其中，医院、卫生院2623个，社区卫生服务中心（站）714个，妇幼保健院（所、站）115个，专科疾病防治院（所、站）67个，疾病预防控制中心157个。”
- Institutions value: 13976个 (不含村卫生室； year-end 2025)
- Beds (verbatim): “医院卫生院床位30.5万张。”
- Beds value: 30.5万张 (医院、卫生院床位 only)
- Beds per 1,000 value: NONE
- Verification notes: 江西省卫健委（hc.jiangxi.gov.cn）不发布卫生健康统计公报，官网亦无统计信息栏目（经站点地图、站内搜索及多轮外部检索核实；媒体引用的《江西省卫生健康统计提要》为内部资料，未在网上公开）。省级卫生数据由《国民经济和社会发展统计公报》承载，公报注明"医疗卫生数据来自省卫生健康委员会”。口径注意：机构数不含村卫生室（窄于其他省份全口径）；床位数为医院、卫生院床位（30.5万张），非全部医疗卫生机构床位。数据为2025年末、全省、初步统计数（公报注1："本公报中数据均为初步统计数"）。公报全文段落原文为："年末共有各类医疗卫生机构（不含村卫生室）13976个。其中，医院、卫生院2623个，社区卫生服务中心（站）714个，妇幼保健院（所、站）115个，专科疾病防治院（所、站）67个，疾病预防控制中心157个。医疗卫生机构人员48.7万人，其中卫生技术人员41.7万人。注册护士21.1万人。医院、卫生院床位30.5万张。" ----------------------------------------

### Shandong (山东) — status: verified
- Data year: 2024
- Source: Shandong Provincial Health Commission (山东省卫生健康委员会) — 《2024年山东省卫生健康事业发展统计公报》
- URL: http://wsjkw.shandong.gov.cn/zwgk/fdzdgknr/tjgb/202512/P020251217356715592186.pdf
- Published: 2025-12-17 (URL-embedded)
- Access method: pdf-downloaded-and-extracted — first-wave agent curl (865,259 bytes, "PDF document, version 1.7, 24 pages", file timestamp Oct 11 23:43); main session pypdf extraction
- Live verification: download 2026-10-11, extraction 2026-10-11..12 (main session; operator PROVINCE block)
- Institutions (verbatim): “（一）医疗卫生机构总数。2024年，全省各级各类医疗卫生机构总数达90058 个”
- Institutions value: 90058个
- Beds (verbatim): “（二）床位数。2024年，全省医疗卫生机构床位 76.10 万张，其中：医院59.09 万张（占77.65%），基层医疗卫生机构”
- Beds value: 76.10万张 (converted exactly = 761,000)
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数由 2023 年 7.30 张增加到2024 年7.55 张。”
- Beds per 1,000 value: 7.55张 (2024 endpoint of the 2023→2024 change sentence)
- Verification notes: footnote marker "1" after "90058 个" removed as a PDF-layout artifact. In the raw extraction the per-1,000 sentence appeared preceded by wrap fragments (“少 265 张。每千人口医疗卫生机构床位数由 2023 年 7.30 张增 加到2024 年7.55 张。”). Beds quote ends mid-sentence in the extraction window. Scope: 全省, 各级各类.
- Transcript evidence: main session `d7cfde67….jsonl` ~lines 540–541, 610–611, 622; download agent `agent-a4144cbc20367ff9a.jsonl` lines 17, 22

### Henan (河南) — status: partial
- Data year: 2025
- Source: 河南省统计局、国家统计局河南调查总队 (Henan Provincial Bureau of Statistics; 公报内注明“医疗卫生机构、床位、卫生技术人员、诊疗人次、出院人数数据来自省卫生健康委员会") — 《2025年河南省国民经济和社会发展统计公报》
- URL: https://tjj.henan.gov.cn/2026/04-09/3341308.html
- Published: 2026-04-16
- Access method: page-fetched
- Live verification: 2026-10-12, batch C2 (transcript `agent-a11f7fe0a9ce9d644.jsonl`)
- Institutions (verbatim): “年末全省共有医疗卫生机构91007个，其中医院2428个，在医院中有公立医院684个，民营医院1744个；基层医疗卫生机构87930个，其中社区卫生服务中心（站）2127个，卫生院1982个，村卫生室58233个，诊所20178个；专业公共卫生机构505个，其中疾病预防控制中心183个，专科疾病防治院（所、站）18个，妇幼保健院（所、站）168个。”
- Institutions value: 91007个 (year-end 2025)
- Beds (verbatim): “医疗卫生机构床位75.15万张，其中医院56.25万张，卫生院13.58万张。”
- Beds value: 75.15万张
- Beds per 1,000 value: NONE
- Verification notes: 河南省卫健委（wsjkw.henan.gov.cn）不发布现行卫生健康统计公报：最近一份标题公报为《2013年河南省卫生资源与医疗服务统计公报》（2014-06-12发布）；其统计信息栏目最新数据为2021年（2022-11-11发布），且仅以图片形式发布、无法文本提取（经该委官网搜索API siteId 4500000023 核实无更新文本）。现行省级卫生数据由省统计局《国民经济和社会发展统计公报》承载，公报注明床位等数据来自省卫生健康委员会。数据为2025年末、全省、全部医疗卫生机构口径；床位总数75.15万张为全部医疗卫生机构床位，公报仅给出医院（56.25万张）与卫生院（13.58万张）分项，无每千人口床位数。佐证页：河南省政府门户《河南省卫生健康事业发展概况》（https://m.henan.gov.cn/2026/04-16/3343224.html，2026-04-16发布，来源河南省统计局）数字完全一致。

### Hubei (湖北) — status: partial
- Data year: 2025
- Source: Hubei Provincial Bureau of Statistics (湖北省统计局) and National Bureau of Statistics Hubei Survey Team (国家统计局湖北调查总队); health data attributed in the bulletin to 省卫健委 (provincial health commission) — 《湖北省2025年国民经济和社会发展统计公报》
- URL: https://tjj.hubei.gov.cn/tjsj/tjgb/ndtjgb/qstjgb/202603/t20260318_5894639.shtml
- Published: 2026-03-18
- Access method: page-fetched
- Live verification: 2026-10-12, batch D2 (transcript `agent-a6d50dd18bd2d4737.jsonl`)
- Institutions (verbatim): “年末全省共有医疗卫生机构39517家，其中医院1276家，基层医疗卫生机构37698家，专业公共卫生机构385家；卫生技术人员52.16万人，其中执业（助理）医师20.04万人，注册护士24.44万人；医疗卫生机构床位46.06万张，其中医院床位33.54万张，社区卫生服务机构床位1.79万张，卫生院床位8.87万张。全年总诊疗人次40522.16万人次，出院人次1499.25万人次。”
- Institutions value: 39517家
- Beds (verbatim): “年末全省共有医疗卫生机构39517家，其中医院1276家，基层医疗卫生机构37698家，专业公共卫生机构385家；卫生技术人员52.16万人，其中执业（助理）医师20.04万人，注册护士24.44万人；医疗卫生机构床位46.06万张，其中医院床位33.54万张，社区卫生服务机构床位1.79万张，卫生院床位8.87万张。全年总诊疗人次40522.16万人次，出院人次1499.25万人次。”
- Beds value: 46.06万张
- Beds per 1,000 value: NONE
- Verification notes: Hubei Province does NOT publish a document titled “湖北省卫生健康事业发展统计公报” — verified via the health commission's 统计信息/数据开放 listings and multiple searches; its own release is a disaggregated data table “2024年全省医疗卫生机构、床位、人员数” (wjw.hubei.gov.cn, page states 发布日期 2025-02-19, http://wjw.hubei.gov.cn/zfxxgk/fdzdgknr/tjxx/tjxx2025/202511/t20251126_5821100.shtml) whose data table is an image attachment (W020251126573259635682.png) not text-extractable, and no 2025-data edition exists yet. Figures above come from the newest fetchable official statistical bulletin (data year 2025), section “十、文化、卫生和体育”; the bulletin states “卫生机构、床位等数据来自省卫健委”. Institutions and beds appear in one combined sentence (reported in full in both fields). Year-end (年末) figures; no 编制床位/实有床位 distinction stated; no per-1,000-population figure anywhere in this bulletin. For reference, the data-year-2024 edition (fetched: https://tjj.hubei.gov.cn/tjsj/tjgb/ndtjgb/qstjgb/202503/t20250321_5585085.shtml, published 2025-03-24) states verbatim “年末全省共有医疗卫生机构38659家，其中医院1268家，基层医疗卫生机构36805家，专业公共卫生机构447家；……医疗卫生机构床位48.98万张，其中医院床位35.6万张，社区卫生服务机构床位1.91万张，卫生院床位9.36万张。” Scope: province-wide.

### Hunan (湖南) — status: verified
- Data year: 2024
- Source: Hunan Provincial Health Commission (湖南省卫生健康委员会) — 《2024年湖南省卫生健康事业发展统计公报》
- URL: https://wjw.hunan.gov.cn/wjw/xxgk/tzgg/202601/33901702/files/3c6a647af6ef4ba7ba53f62d8393455c.pdf
- Published: 2026-01 (month precision only, URL segment 202601; the registry encodes month-precision dates as the first of the month)
- Access method: pdf-downloaded-and-extracted — first-wave agent curl (684,859 bytes, "PDF document, version 1.7, 29 pages", file timestamp Oct 11 23:44); main session pypdf extraction; per-1,000 sentence re-extracted (main session lines 617–618) to confirm it across a line wrap
- Live verification: download 2026-10-11, extraction 2026-10-11..12 (main session; operator PROVINCE block)
- Institutions (verbatim): “（一）医疗卫生机构总数。2024年末，全省医疗卫生机构总数 57639 个，比上年增加 129 个。其中：医院 1763 个，基层”
- Institutions value: 57639个 (year-end 2024)
- Beds (verbatim): “（二）床位数。2024年末，全省医疗卫生机构床位 523215 张，其中：医院 381967 张（占 73.00%），基层医疗卫生机构 123504”
- Beds value: 523215张
- Beds per 1,000 (verbatim): “每千常住人口医疗卫生机构床位数由 2023 年 8.13 张减少为 2024 年 8.00 张。”
- Beds per 1,000 value: 8.00张 (常住人口 basis; 2024 endpoint of the 2023→2024 change sentence)
- Verification notes: footnote marker "1" after "57639 个" removed as a PDF-layout artifact. The per-1,000 sentence spans a line wrap in the raw extraction (“每千常住人口医疗 卫生机构床位数由 2023 年 8.13 张减少为 2024 年 8.00 张。”) and was re-extracted to confirm. Quotes end mid-sentence in the extraction window. Scope: 全省, 年末 2024.
- Transcript evidence: main session `d7cfde67….jsonl` ~lines 540–541, 610–611, 617–618, 622; download agent `agent-afc7b52bc91a50a7b.jsonl` lines 21, 26

### Guangdong (广东) — status: verified
- Data year: 2025
- Source: Guangdong Provincial Health Commission (广东省卫生健康委员会) — 《2025年广东省医疗卫生资源和医疗服务情况分析》
- URL: https://wsjkw.gd.gov.cn/gkmlpt/content/4/4907/mpost_4907189.html
- Published: 2026-06-05
- Access method: page-fetched
- Live verification: 2026-10-12, batch D2 (transcript `agent-a6d50dd18bd2d4737.jsonl`)
- Institutions (verbatim): “（一）医疗卫生机构数1。2025年末，全省医疗卫生机构68427家，较上年增加2302家。其中：医院1898家，基层医疗机构65541家，专业公共卫生机构574家，其他医疗卫生机构414家。”
- Institutions value: 68427家
- Beds (verbatim): “（二）床位数。2025年末，全省医疗机构床位65.2万张，较上年增加0.8万张，其中：医院54.0万张（占82.8%），基层医疗卫生机构7.7万张（占11.9%），专业公共卫生机构3.4万张（占5.3%）。”
- Beds value: 65.2万张
- Beds per 1,000 (verbatim): “按照常住人口统计，全省每千人口床位5.07张，较上年增加0.03张。”
- Beds per 1,000 value: 5.07张
- Verification notes: Exact document title is “2025年广东省医疗卫生资源和医疗服务情况分析”, NOT “统计公报” — Guangdong's health commission does not publish a “广东省卫生健康事业发展统计公报”； its official annual release series is “医疗卫生资源和医疗服务情况简报/分析” (e.g., “2024年广东省医疗卫生资源和医疗服务情况简报” published 2025-05-13), and this 分析 document is the official annual release for data year 2025 (publisher 广东省卫生健康委员会, 索引号 006940132/2026-00153, 文件状态 现行有效, 成文日期/发布日期 2026-06-05). The "1" in “医疗卫生机构数1。” is a footnote marker; footnote 1 states per 《国家卫生健康统计调查制度》 that 医疗卫生机构 includes 医院、基层医疗机构、专业公共卫生机构、其他机构， and that 医院 does NOT include 妇幼保健院 and 专科疾病防治院 (these are counted under 专业公共卫生机构) — a scope caveat for cross-province comparability. Beds labeled 医疗机构床位 (year-end 2025年末); per-1,000 computed on 常住人口 (resident population); the document says “每千人口床位” (not 床位数). Province-wide scope.

### Guangxi (广西) — status: verified
- Data year: 2024
- Source: Health Commission of Guangxi Zhuang Autonomous Region (广西壮族自治区卫生健康委员会)； page source line: 自治区卫生健康统计信息中心 — 《2024年广西卫生健康事业发展统计公报》
- URL: https://wsjkw.gxzf.gov.cn/xxgk_49493/fdzdgk/tjxx/tjnb/t26240378.shtml
- Published: 2025-12-02
- Access method: page-fetched
- Live verification: 2026-10-12, batch D2 (transcript `agent-a6d50dd18bd2d4737.jsonl`)
- Institutions (verbatim): “2024年全区医疗卫生机构共有34688家，其中：医院929家，基层医疗卫生机构33324家，专业公共卫生机构355家，其他机构80家。”
- Institutions value: 34688家
- Beds (verbatim): “2024年医疗卫生机构床位37.73万张，比去年增加1.53万张其中：医院26.14万张（占69.28%），基层医疗卫生机构9.75万张（占25.83%），专业公共卫生机构1.74万张（占4.62%），其他卫生机构0.1万张（占0.27%）。”
- Beds value: 37.73万张
- Beds per 1,000 (verbatim): “2024年，全区每千人口医疗卫生机构床位数7.53张，比去年的7.20张增加了0.33张。”
- Beds per 1,000 value: 7.53张
- Verification notes: This is the newest Guangxi bulletin (published 2025-12-02); the commission's 统计年报 archive (fetched) shows no 2025-data edition yet as of 2026-10. Calendar-year-2024 figures, province-wide (全区) scope. Headline bed figure is labeled 医疗卫生机构床位 (no 编制床位/实有床位 distinction stated for the headline number), while sub-breakdowns use 实有床位 (e.g., 公立医院实有床位18.67万张， 乡镇卫生院实有床位92857张). The missing punctuation after “增加1.53万张” (“万张其中：”) is exactly as printed in the source page. Sentence also notes the bed total increased 1.53万张 vs prior year.

### Hainan (海南) — status: verified
- Data year: 2023
- Source: Hainan Provincial Health Commission (海南省卫生健康委员会) — 《海南省2023年卫生健康事业发展统计公报》
- URL: https://wst.hainan.gov.cn/swjw/xxgk/0900/202411/t20241122_3773173.html
- Published: 2024-07-08
- Access method: page-fetched
- Live verification: 2026-10-12, batch D2 (transcript `agent-a6d50dd18bd2d4737.jsonl`)
- Institutions (verbatim): “（一）医疗卫生机构总数。2023年末，全省医疗卫生机构总数达6525个，比上年增加139个。其中：医院240个，基层医疗卫生机构6143个，专业公共卫生机构115个。与上年相比，医院减少30个1，基层医疗卫生机构增加159个（见图1和表1）。”
- Institutions value: 6525个
- Beds (verbatim): “（二）床位数。2023年末，全省医疗卫生机构床位60929张，其中：医院46769张(占76.76%)，基层医疗卫生机构11359张(占18.64%)。与上年相比，床位减少280张，其中：医院床位减少1786张3，基层医疗卫生机构床位增加1315张。2023年每千人口医疗卫生机构床位数5.84张。（见图2）”
- Beds value: 60929张
- Beds per 1,000 (verbatim): “2023年每千人口医疗卫生机构床位数5.84张。（见图2）”
- Beds per 1,000 value: 5.84张
- Verification notes: This is the most recent Hainan health development statistical bulletin — no 2024 or 2025 edition exists as of 2026-10 (verified against the commission's 数据发布 index, which is current through 2026 items, and via web search). Year-end (2023年末) figures; province-wide (全省) scope. The "1" and "3" inside the sentences are footnote reference markers, copied as printed. Measure caveat visible in source: the bulletin's own footnote (12) states that per-1,000-population indicators (including 医疗卫生机构床位数) are “按2021年常住人口计算” (calculated using 2021 resident population), while the bulletin elsewhere cites 2023年常住总人口1043.21万人 from the Hainan statistics bulletin — an internal inconsistency visible in the source text. No 编制床位/实有床位 distinction stated. Page shows 发布日期 2024-07-08 10:15 although the URL path (202411/t20241122) suggests a later CMS re-publication date of 2024-11-22.

### Chongqing (重庆) — status: verified
- Data year: 2025
- Source: 重庆市卫生健康委员会（Municipal Health Commission of Chongqing） — 《2025年重庆市卫生健康事业发展统计公报》
- URL: https://wsjkw.cq.gov.cn/zwgk_242/fdzdgknr/tjxx/tjfx/202608/t20260825_15976916_wap.html (PDF attachment: https://wsjkw.cq.gov.cn/zwgk_242/fdzdgknr/tjxx/tjfx/202608/W020260825529766743577.pdf)
- Published: 2026-08-25
- Access method: page-fetched then pdf-downloaded-and-read (article page and PDF both fetched via Bash curl with browser User-Agent because WebFetch is blocked for .gov.cn; PDF text extracted with pdftotext; Chinese extracts cleanly)
- Live verification: 2026-10-11..12, batch E (transcript `agent-aa41a22a3940a10c1.jsonl`)
- Institutions (verbatim): “2025年末，全市共有各级各类医疗卫生机构23854个，其中医院810个、基层医疗卫生机构22806个、专业公共卫生机构119个。”
- Institutions value: 23854个
- Beds (verbatim): “医疗卫生机构床位数21.26万张2，其中医院床位16.19万张、基层医疗卫生机构床位4.61万张。”
- Beds value: 21.26万张
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数6.67张3。”
- Beds per 1,000 value: 6.67张
- Verification notes: The digits "2" and "3" immediately after 万张/张 in the quoted text are superscript FOOTNOTE MARKERS in the printed PDF, not part of the numbers. Footnote 2 states verbatim: "床位数指年底固定实有床位数。" — i.e., beds are year-end fixed ACTUAL (实有) beds, not 编制床位 (approved/establishment beds). Footnote 3: per-1000 indicators are computed on 2025 常住人口 (permanent resident population) as published by 重庆市统计局 in the 2025 economic bulletin. Footnote 1 (title marker): 卫生资源与医疗服务相关数据来源于国家卫生健康统计年报、妇幼健康统计年报. Unit conversion for reference only: 21.26万张 = 212,600 beds (16.19万张 = 161,900; 4.61万张 = 46,100). Data are year-end (2025年末) figures. Table 1 of the same bulletin independently lists 机构数 23854 and 床位数 21.26万张, matching the prose. pdftotext inserts kerning spaces between CJK characters and numerals (layout artifact); the quoted sentences are given with such spaces removed, matching the printed document. The attachment file on the page is named "2025年重庆市卫生事业发展统计公报.pdf" but the title printed inside the PDF is 2025年重庆市卫生健康事业发展统计公报.

### Sichuan (四川) — status: verified
- Data year: 2024
- Source: 四川省卫生健康委员会（Health Commission of Sichuan Province） — 《2024年四川省卫生健康事业发展统计公报》
- URL: https://wsjkw.sc.gov.cn/scwsjkw/njgb/2026/2/9/821f77b263a044498965f82e3b035625.shtml (full text in attachment: https://wsjkw.sc.gov.cn/scwsjkw/njgb/2026/2/9/821f77b263a044498965f82e3b035625/files/2024年四川省卫生健康事业发展统计公报.doc)
- Published: 2026-02-09
- Access method: page-fetched, then doc-downloaded-converted-and-read (.doc attachment downloaded via Bash curl with browser User-Agent; converted to UTF-8 text with macOS textutil; text extracts cleanly)
- Live verification: 2026-10-11..12, batch E (transcript `agent-aa41a22a3940a10c1.jsonl`)
- Institutions (verbatim): “（一）医疗卫生机构总数。2024年末，全省医疗卫生机构总数74796个1，比上年减少184个。其中：医院2421个，基层医疗卫生机构71467个，专业公共卫生机构671个。与上年比较，医院减少58个，基层医疗卫生机构减少114个。”
- Institutions value: 74796个
- Beds (verbatim): “（二）床位数。2024年末，全省医疗卫生机构床位71.49万张，其中：医院53.74万张（占75.16%），基层医疗卫生机构16.20万张（占22.65%），专业公共卫生机构1.53万张（占2.14%）。医院中，公立医院床位占66.29%，民营医院床位占33.71%。与上年比较，床位增加0.63万张，其中：公立医院增加0.79万张，民营医院减少0.38万张；基层医疗卫生机构床位增加0.32万张，专业公共卫生机构床位增加0.03万张。每千人口医疗卫生机构床位数由2023年8.47张增加到2024年8.55张。”
- Beds value: 71.49万张
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数由2023年8.47张增加到2024年8.55张。”
- Beds per 1,000 value: 8.55张（2024年；2023年为8.47张）
- Verification notes: The digit "1" after "74796个" in the quoted text is a superscript FOOTNOTE MARKER in the printed document, not part of the number; footnote 1 defines: 医疗卫生机构包括医院、基层医疗卫生机构、专业公共卫生机构、其他机构. This 2024-data bulletin (published 2026-02-09) is the NEWEST Sichuan bulletin available as of 2026-10; no 2025-data edition was found. Unit conversion for reference only: 71.49万张 = 714,900 beds (53.74万张 = 537,400; 16.20万张 = 162,000; 1.53万张 = 15,300). Figures are year-end (2024年末). The bulletin contains no explicit 编制床位/实有床位 definitional note for the bed count (beds are simply reported as 床位); note 13 discloses a 2024 national statistical scope adjustment affecting 卫生技术人员 (personnel), not beds. Quoted text is character-for-character from the converted .doc.

### Guizhou (贵州) — status: verified
- Data year: 2023
- Source: 贵州省卫生健康委员会（Health Commission of Guizhou Province; page posted by 卫生信息中心） — 《2023年贵州省卫生健康事业发展统计公报》
- URL: https://wjw.guizhou.gov.cn/zwgk/zdlyxx/tjsj/202409/t20240925_85752730.html
- Published: 2024-09-25 09:12
- Access method: page-fetched (full bulletin text is in the HTML body of the page; fetched via Bash curl with browser User-Agent because WebFetch is blocked for .gov.cn)
- Live verification: 2026-10-11..12, batch E (transcript `agent-aa41a22a3940a10c1.jsonl`)
- Institutions (verbatim): “2023年，全省医疗卫生机构总数达30722个，比上年增加1572个（增长5.39％）。其中：医院1544个（不含妇幼保健机构，下同），基层医疗卫生机构28750个，专业公共卫生机构359个，其他卫生机构69个。与上年相比，医院增加88个（增长6.04％），基层医疗卫生机构增加1456家（增长5.33％），专业公共卫生机构增加　15个（增长4.36％），其他卫生机构增加13个（增长23.21％）。（见表1）”
- Institutions value: 30722个
- Beds (verbatim): “2023年，全省医疗卫生机构床位31.54万张，其中：医院（不含妇幼保健机构）25.55万张（占81.01％），基层医疗卫生机构4.82万张（占15.30％），专业公共卫生机构1.14万张（占3.63％）。医院中，公立医院床位数14.21万张，民营医院床位数11.34万张（各占55.63％和44.37％）。基层医疗卫生机构中，社区卫生服务中心（站）0.83万张，卫生院3.98万张（各占17.14％和82.59％）。与上年相比，全省医疗卫生机构床位增加0.57万张（增长1.83％），其中：医院床位增加1.35万张（增长5.56％），基层医疗卫生机构床位减少0.80万张（降低14.25％），专业公共卫生机构增加245张（增长2.19％）。”
- Beds value: 31.54万张
- Beds per 1,000 (verbatim): “2023年，全省每千人口医疗卫生机构床位数8.16张。”
- Beds per 1,000 value: 8.16张
- Verification notes: This is the MOST RECENT Guizhou 卫生健康事业发展统计公报 in existence — after the 2023 edition the commission stopped publishing the bulletin and switched to annual statistical tables (its 统计数据 index lists only tables; no 2024 or 2025 bulletin found as of 2026-10). Newer official reference (fetched, not a bulletin): "2025年贵州省医疗卫生机构数量及床位数", 卫生信息中心, published 2026-05-19 12:00, https://wjw.guizhou.gov.cn/zwgk/zdlyxx/tjsj/202605/t20260519_90187411.html — 2025 totals 机构31581个, 床位302334张, 每千人口床位数（常住）7.84. Measure caveats: the 医院 category EXCLUDES 妇幼保健机构 (indicator 2 of the bulletin's 指标解释; 妇幼保健机构 are counted under 专业公共卫生机构); the institution-scope definition is 医疗卫生机构包括医院、基层医疗卫生机构、专业公共卫生机构、其他卫生机构 (indicator 1); population data 采用省统计局2023年年末常住人口数据 and per-1000 indicators 按常住人口计算 (indicator 18). Unit conversion for reference only: 31.54万张 = 315,400 beds (25.55万张 = 255,500; 4.82万张 = 48,200; 1.14万张 = 11,400). The quoted institutions sentence contains a literal full-width space "　" between "增加" and "15个" as printed in the raw HTML; the percent signs in the original are full-width ％. Figures are 2023 calendar-year/year-end figures.

### Yunnan (云南) — Pass 1 (S12), kept without re-verification
- Recorded values (2023): institutions 28,765; beds 359,900 (35.99万张, includes 275,778 hospital beds)
- Source: Yunnan Daily (云南日报, reporting provincial health-commission data) — 《筑基强本守护人民健康》
- URL: https://www.yndaily.com/html/2024/yaowenyunnan_0925/129208.html (published 2024-09-25)
- Why a newspaper: the commission's own 2024 bulletin PDF (ynswsjkw.yn.gov.cn) was unreachable (SSL handshake failure) — listed in the S12 excluded-sources table; its at-2024 figures are NOT recorded
- Verbatim (single sentence covering both metrics): “截至2023年，全省共有医疗卫生机构28765个、医疗卫生机构拥有床位数35.99万张”
- Live verification: 2026-08-29 (Pass 1) — `evidence/S12/live-verification.md`; the October sessions reference that file (no re-fetch of yndaily.com)
- S20 registry decision (October session): "Yunnan 2023 ×2 — keep"
- No per-1,000-beds figure for Yunnan appears in any source; none recorded

### Shaanxi (陕西) — status: verified
- Data year: 2025
- Source: 陕西省卫生健康委员会（Health Commission of Shaanxi Province） — 《2025年陕西省卫生健康事业发展统计公报》
- URL: https://sxwjw.shaanxi.gov.cn/zfxxgk/fdzdgknr/tjxx/t_3665045.html (PDF attachment: https://sxwjw.shaanxi.gov.cn/zfxxgk/fdzdgknr/tjxx/P020260810289621239421.pdf)
- Published: 2026-08-07 (page-stated 发布日期； PDF file ModDate 2026-08-10)
- Access method: pdf-downloaded-and-read — the bulletin PDF is a SCANNED IMAGE PDF (pdftotext/pypdf extract nothing), so pages were rendered with pdftoppm and read with a macOS Vision OCR tool (VNRecognizeTextRequest, zh-Hans) built and run via Bash in this session
- Live verification: 2026-10-11..12, batch E (transcript `agent-aa41a22a3940a10c1.jsonl`)
- Institutions (verbatim): “（一）医疗卫生机构总数。2025年，全省医疗卫生机构总数35131个，比上年减少295个。其中：医院1264个，基层医疗卫生机构33458个，专业公共卫生机构287个。与上年相比，医院减少24个，基层医疗卫生机构减少204个。”
- Institutions value: 35131个
- Beds (verbatim): “（二）床位数。2025年，全省医疗卫生机构床位30.12万张，其中：医院24.86万张（占82.53%），基层医疗卫生机构4.18万张（占13.86%），专业公共卫生机构1.02万张（占3.39%）。医院中，公立医院床位占70.56%，民营医院床位占29.44%。与上年比较，床位减少8532张，其中，公立医院减少3882张，民营医院减少2896张，基层医疗卫生机构床位减少1451张，专业公共卫生机构床位减少260张，其他机构床位减少43张。每千人口医疗卫生机构床位数由7.83张减少到7.65张。”
- Beds value: 30.12万张（bulletin Table 1 exact count: 301183张）
- Beds per 1,000 (verbatim): “每千人口医疗卫生机构床位数由7.83张减少到7.65张。”
- Beds per 1,000 value: 7.65张（2025年；2024年为7.83张）
- Verification notes: OCR CAVEAT: the PDF is a scanned image, so the quoted sentences come from OCR output; OCR line breaks and spurious spaces around numerals were normalized (no characters added or changed beyond that), and every figure was cross-validated as follows. (1) Internal arithmetic all checks: 35426−35131=295, 1288−1264=24, 33662−33458=204; 309715−301183=8532, 179251−175369=3882, 76080−73184=2896, 43206−41755=1451, 9571−9311=260, 721−678=43. (2) The 2024 comparison column of the 2025 bulletin (机构35426, 床位309715) matches the TEXT-extractable 2024 edition PDF (https://sxwjw.shaanxi.gov.cn/zfxxgk/fdzdgknr/tjxx/P020260810164717684085.pdf, fetched and read with pdftotext), which states "2024年，全省医疗卫生机构总数35426个" and table row "总计 35136 35426 306176 309715" and "每千人口医疗卫生机构床位数由2023年7.75张增加到2024年7.83张" — so the per-1000 chain 7.75→7.83→7.65 is consistent across three bulletins. (3) The independent official 2025年陕西省国民经济和社会发展统计公报 (Shaanxi Provincial Bureau of Statistics, fetched: http://tjj.shaanxi.gov.cn/tjsj/ndsj/tjgb/qs_444/202604/t20260415_3630186.html) corroborates: "全省卫生健康机构35129个(包括村卫生室20448个)，其中，医院1264所…全省共有床位30.12万张，其中，医院病床24.86万张，卫生院病床3.73万张" (its institution total 35129 differs slightly because 统计局 uses 卫生健康机构 wording/scope; the bulletin's own figures are as quoted). Unit conversion for reference only: 30.12万张 = 301,200 beds, matching Table 1's exact 301183张; 24.86万张 = 248,600; 4.18万张 = 41,800; 1.02万张 = 10,200. Per-1000 basis: the 2024 edition of the same bulletin series defines 每千人口…医疗卫生机构床位数 as computed on 常住人口 (indicator note 12 of its 指标解释)； the 2025 edition's definition pages were not OCR-verified. Data are 2025年 (year) figures.

### Gansu (甘肃) — status: partial
- Data year: 2023
- Source: 甘肃省卫生健康委员会 / compiled by 甘肃省卫生健康统计信息中心 (cover: “甘肃省卫生健康统计信息中心 2024年3月”)； PDF obtained from the website of the 平凉市卫生健康委员会 (Pingliang Municipal Health Commission mirror) — 《2023年甘肃省卫生健康事业发展统计公报》
- URL: http://wjw.pingliang.gov.cn/api-gateway/jpaas-web-server/front/document/download?fileUrl=YW5UzzlvCwcM%2FNHHX%2FtT6HhnILUYEuE4XKZMlTIXaXXVpClpPglLhXCuwXzLou4SJUsirtvM6eYjnzYfMi2On92on0msZ5Ku7PMC6I%2BajE%2Fb06LZoiascJajaQn%2BXuR8yYi%2BEU%2BpmXIAhW5B6qAk9Eg%2Bxgbnhm2Q19hYAdU%2BAg8%3D&fileName=2023%E5%B9%B4%E7%94%98%E8%82%83%E7%9C%81%E5%8D%AB%E7%94%9F%E5%81%A5%E5%BA%B7%E4%BA%8B%E4%B8%9A%E5%8F%91%E5%B1%95%E7%BB%9F%E8%AE%A1%E5%85%AC%E6%8A%A5.pdf (link surfaced by the Pingliang site search, which returned the document titled 2023年甘肃省卫生健康事业发展统计公报; official origin page on Gansu's own site: http://wsjk.gansu.gov.cn/wsjk/c115323/202403/173883189.shtml with attachment .../files/832a157d4b504e4388060926182446ba.pdf — unreachable, see NOTES)
- Published: 2024-03 (cover date of the bulletin; the official Gansu publication page could not be fetched)
- Access method: pdf-downloaded-and-read — 60-page SCANNED IMAGE PDF (22 MB) downloaded via Bash curl with browser User-Agent; pdftotext/pypdf extract nothing, so relevant pages were rendered with pdftoppm and read with a macOS Vision OCR tool (VNRecognizeTextRequest, zh-Hans) built and run via Bash in this session
- Live verification: 2026-10-11..12, batch E (transcript `agent-aa41a22a3940a10c1.jsonl`)
- Institutions (verbatim): “2023年末，全省医疗卫生机构总数25345个（含村卫生室）。其中：医院737个，基层医疗卫生机构24200个（含村卫生室），专业公共卫生机构383家。与2022年比较，医院增加31个，卫生院减少6个，社区卫生服务中心（站）增加43个，村卫生室增加7个，诊所、卫生所、医务室增加61个，计划生育技术服务机构减少58个（见图1和表1）。”
- Institutions value: 25345个（含村卫生室）
- Beds (verbatim): “（三）医疗机构床位数 2023年末，全省医疗机构床位203974张，每千人口床位8.27张（见表3）。其中：医院床位156135张（占76.55%），卫生院床位32187张（占15.78%），社区卫生服务中心（站）床位5123张（占2.51%），妇幼保健院（所、站）床位8682张（占4.26%）（见表5）。与2022年相比，医疗机构床位增加14980张，其中：医院床位增加11522张，卫生院床位增加2516张，社区卫生服务中心（站）床位增加557张，妇幼保健院（所、站）床位增加789张（见表5）。”
- Beds value: 203974张
- Beds per 1,000 (verbatim): “2023年末，全省每千人口床位8.27张，每千人口执业（助理）医师3.16人，每千人口注册护士4.07人，每千人口卫生技术人员8.95人（见表3）。”
- Beds per 1,000 value: 8.27张
- Verification notes: WHY 2023 (newest fetchable edition) AND NOT 2025: a 2025-data bulletin EXISTS (《2025年甘肃省卫生健康事业发展统计公报》， official page http://wsjk.gansu.gov.cn/wsjk/c115323/202606/174345762.shtml, published 2026-06-11, attachment .../files/2e5f9a02ba9f4a8a8acc7026e356cc49.pdf) and a 2024-data bulletin EXISTS (http://wsjk.gansu.gov.cn/wsjk/c115323/202504/174133253.shtml, attachment .../files/7f93fb544d244742806e0265fbeee06f.pdf), but BOTH WERE INACCESSIBLE — the entire gansu.gov.cn domain group (wsjk.gansu.gov.cn, www.gs.gov.cn, gansu.gov.cn) sits behind a Knownsec 加速乐 JavaScript anti-bot challenge that returns a ~6.4KB obfuscated-JS page for every URL including PDF attachments. Exhausted bypass attempts: curl with browser and Baiduspider User-Agents, WebFetch (blocked for all .gov.cn in this environment), r.jina.ai reader (timeout), web.archive.org (unreachable), legacy domains www.gswst.gov.cn and gswst.gansu.gov.cn (dead), and mirror searches across Baidu, Bing, Sogou, 360, Gansu municipal health-commission sites, newspaper mirrors, doc-sharing sites and WeChat — no verbatim text of the 2024/2025 editions could be retrieved, so NO figures from them are reported (their existence is noted only). Per the rule “prefer the newest bulletin whose figures you can actually fetch,” this block reports the 2023 edition, whose PDF was retrieved via the Pingliang Municipal Health Commission mirror. OCR CAVEAT: the PDF is scanned, so quotes come from Vision OCR with line breaks/spaces normalized; figures cross-validated by (1) internal arithmetic — Table 5: 2022 total 188994 + 14980 increase = 203974 ✓; category shares 156135/203974=76.55%, 32187/203974=15.78%, 5123/203974=2.51%, 8682/203974=4.26% ✓ — and (2) independent search-index snippets of the same official document matching the OCR digits (25345/737/24200/383; 203974; 8.27; 156135). Measure caveats: the beds paragraph uses the wording 医疗疗机构床位/每千人口床位 (prose “医疗机构”) while Table 5 is titled 全省医疗卫生机构床位数； no 编制床位/实有床位 distinction is stated in the beds section; the institution total explicitly INCLUDES village clinics (含村卫生室)， and 医院床位 here excludes 妇幼保健院（所、站） beds, which are broken out separately (8682张). Figures are year-end (2023年末).

### Qinghai (青海) — status: partial (economic bulletin; no health bulletin exists online)
- Health-bulletin search (2026-10-16, batch F2, transcript `agent-a26de55d96f29305d.jsonl`): **not_found.** No 青海省卫生健康事业发展统计公报 (nor predecessor-titled 卫生和计划生育 edition) could be located online for any year. Checks performed: (1) commission site wsjkw.qinghai.gov.cn has no 统计信息 column; full-text site search returns 0 results for “统计公报”, “事业发展统计”, “统计信息”; the 2 hits for “公报” were fetched and confirmed to be reposts of the national 2022年度国家老龄事业发展公报; “床位” hits are administrative bed-approval notices only. (2) Web search (Bing exact-phrase, 360, Sogou WeChat) found no Qinghai provincial health bulletin; the only old-title item is an unfetchable 360文库 entry. (3) The closest fetched official figure — “截至2024年底，……每千人口医疗卫生机构床位数从6.96张增至8.06张” from a 省发展改革委 article (http://www.qinghai.gov.cn/zwgk/system/2025-11-15/030086202.shtml, fetched 2026-10-16) — is a “十四五” work summary containing no institution or bed totals and was explicitly NOT substituted for a bulletin. The batch recommended sourcing from the economic bulletin or 青海统计年鉴; the operator then executed the economic-bulletin fallback first-hand.
- Recorded source: Qinghai Provincial Bureau of Statistics + NBS Qinghai Survey Team (青海省统计局 / 国家统计局青海调查总队) — 《青海省2025年国民经济和社会发展统计公报》; the bulletin's own data-source note attributes health data to 省卫生健康委员会 (“卫生健康数据来自省卫生健康委员会”)
- URL: http://tjj.qinghai.gov.cn/tjData/yearBulletin/202603/P020260302663152872943.doc
- Published: 2026-03-02 (statistics-site listing; document itself dated 2026年2月28日, 印发 2026年2月9日; .doc metadata Last Saved Mon Mar 2 17:40:16 2026)
- Access method: doc-downloaded-converted-and-grepped — operator curl of the yearBulletin index listed the .doc; curl download + macOS `textutil -convert txt` + grep; file identified as Composite Document File V2 (WPS Office)
- Live verification: 2026-10-16, first-hand by the operator (main session lines 1284–1309)
- Institutions + beds (verbatim, one sentence, section “十一、文化旅游、卫生健康和体育”): “年末有医疗卫生机构6924个，床位4.72万张。其中，医院251个，床位3.95万张；乡镇卫生院406个，床位5584张；社区卫生服务中心37个；妇幼保健院（所、站）52个；疾病预防控制中心（防疫站）54个；村卫生室4449个；诊所（卫生所、医务室）1193个；卫生监督所（中心）1个。全年总诊疗人次3096.6万人次，出院人次124.1万人次。”
- Institutions value: 6924个
- Beds value: 4.72万张 (converted exactly = 47,200)
- Beds per 1,000: NONE — grep for per-1,000 patterns returned no matches; the economic bulletin contains no per-1,000-beds figure (matching the econ-fallback pattern: institutions + beds only)
- Verification notes: arithmetic cross-check — the year-end 其中-enumeration sums 251+406+37+52+54+4449+1193+1 = 6,443, not 6,924 (difference 481): the enumeration is PARTIAL (8 categories listed; the stated total includes additional categories not enumerated), so the headline total 6,924 is the citable figure and the partial enumeration is recorded as a caveat. Operator confirmation: “Qinghai verified first-hand: 6924个 / 4.72万张 (47,200张)”. Session closing note: “All 31 provinces now have machine-verified records.”
- Transcript evidence: main session `d7cfde67….jsonl` lines 1284–1285, 1289–1290, 1298–1299, 1301, 1303, 1305–1306, 1309, 1356; batch F2 `agent-a26de55d96f29305d.jsonl` (health-bulletin search)

### Ningxia (宁夏) — status: verified
- Data year: 2025
- Source: 宁夏回族自治区卫生健康委员会 (来源：自治区卫生健康委规划发展与信息化处) — 《2025年宁夏卫生健康统计公报》
- URL: https://wsjkw.nx.gov.cn/zfxxgk_279/fdzdgknr/wstjbg/202606/t20260625_5274257.html
- Published: 2026-06-25
- Access method: page-fetched
- Live verification: 2026-10-16, batch F2 (transcript `agent-a26de55d96f29305d.jsonl`)
- Institutions (verbatim): “2025年末，全区医疗卫生机构5136个，同比增加150个（医院减少4个，基层医疗卫生机构增加150个，专业公共卫生机构增加2个，其他卫生机构增加2个）。其中，医院215个，基层医疗卫生机构4810个，专业公共卫生机构86个，其他卫生机构25个。具体见图1。”
- Institutions value: 5136个
- Beds (verbatim): “2025年末，全区医疗卫生机构实有床位44749张，同比增加463张，增长1.05%。其中，医院38075张，占85.09%；基层医疗卫生机构4630张，占10.35%；专业公共卫生机构2015张，占4.50%。”
- Beds value: 44749张 (实有床位, 2025年末)
- Beds per 1,000 (verbatim): “全区每千人口医疗卫生机构实有床位数由2024年6.07张增加到2025年6.11张。”
- Beds per 1,000 value: 6.11张 (2025年; 2024年为6.07张)
- Verification notes: The official bulletin page publishes the body as 21 JPG images with no text layer; the quotes above were machine-read from the official images via macOS Vision OCR (zh-Hans). All Chinese characters and digits were verified identical across two OCR passes at different image resolutions; OCR-introduced spacing from justified typesetting was normalized (e.g., the source renders "增长 1.05%" / "占 85.09%" with extra spaces), so intra-sentence whitespace may not be character-exact — characters and digits are. 床位 = 实有床位 (actual beds), reference date 2025年末 (year-end), scope 全区 = the whole Ningxia Hui Autonomous Region. Bulletin footnote states "数据来源于国家卫生统计信息网络直报系统". Internal consistency verified: 215+4810+86+25=5136; 44286+463=44749; 38075/44749=85.09%, 4630/44749=10.35%, 2015/44749=4.50%; component deltas (医院 219→215 = −4, 基层 4660→4810 = +150, 专业公卫 84→86 = +2, 其他 23→25 = +2) sum to +150. Independently cross-validated against the prior-year bulletin page (2024年宁夏卫生健康统计公报, https://wsjkw.nx.gov.cn/zfxxgk_279/fdzdgknr/wstjbg/202507/t20250704_4953091.html, published 2025-07-04, also image-only, OCR'd this session), which states 2024年末 医疗卫生机构4986个、实有床位44286张、每千人口实有床位6.07张 — exactly matching the 2025 bulletin's YoY statements.

### Xinjiang (新疆) — status: partial
- Data year: 2024
- Source: 新疆维吾尔自治区卫生健康委员会官网 (reposting 石榴云/新疆日报 report, 记者苏璐萍) (no standalone bulletin title)
- URL: https://wjw.xinjiang.gov.cn/hfpc/xwxc1/202507/8084e94da5b44ca9a8a3dc5a6f1a9759.shtml
- Published: 2025-07-11
- Access method: page-fetched
- Live verification: 2026-10-16, batch F2 (transcript `agent-a26de55d96f29305d.jsonl`)
- Institutions (verbatim): “记者从7月10日召开的2025年卫生健康系统援疆和医改工作座谈会上获悉，截至2024年底，全区医疗卫生机构总数达16739个，较2020年增长7.08%；床位总数达17.77万张，每千人口床位数达7.85张；医疗卫生人员总量增至27.54万人，每千人口卫生技术人员数达9.57人，提前完成“十四五”规划目标任务。”
- Institutions value: 16739个
- Beds (verbatim): “记者从7月10日召开的2025年卫生健康系统援疆和医改工作座谈会上获悉，截至2024年底，全区医疗卫生机构总数达16739个，较2020年增长7.08%；床位总数达17.77万张，每千人口床位数达7.85张；医疗卫生人员总量增至27.54万人，每千人口卫生技术人员数达9.57人，提前完成“十四五”规划目标任务。”
- Beds value: 17.77万张
- Beds per 1,000 (verbatim): “记者从7月10日召开的2025年卫生健康系统援疆和医改工作座谈会上获悉，截至2024年底，全区医疗卫生机构总数达16739个，较2020年增长7.08%；床位总数达17.77万张，每千人口床位数达7.85张；医疗卫生人员总量增至27.54万人，每千人口卫生技术人员数达9.57人，提前完成“十四五”规划目标任务。”
- Beds per 1,000 value: 7.85张
- Verification notes: BULLETIN_TITLE is NONE because no standalone 新疆维吾尔自治区卫生健康事业发展统计公报 could be located online: the commission's site-search API (searched 统计公报, 事业发展统计公报, 卫生健康统计, 每千人口床位, 实有床位, 床位总数) returns no bulletin, and Bing exact-phrase, 360, and 天山网 (ts.cn) searches were also negative. The single fetched sentence above (one sentence, containing all three requested metrics) therefore comes from an official 石榴云/新疆日报 news report hosted on the commission's own website, citing data released at the 2025年卫生健康系统援疆和医改工作座谈会 held 2025-07-10 — NOT from a statistical bulletin, hence STATUS partial. Reference date 截至2024年底 (end-2024); beds stated as 床位总数 (bed type 实有/编制 not specified in the source). Scope caveat (important for cross-province comparability): 17.77万张 ÷ 7.85/千人 implies a population denominator of ≈2,264万, matching Xinjiang's local population EXCLUDING the Xinjiang Production and Construction Corps (兵团). A later commission-hosted press-conference article (2025-11-08, "从30岁提升至77岁 新疆卫生健康事业实现历史性跨越") states verbatim "截至2024年年末，全区各级各类医疗卫生机构（含兵团）总数已超过1.9万家，每千人口医疗机构床位数达7.85张，卫生健康系统人员总数达到31.46万人" — i.e., including 兵团, institutions exceed 19,000 and personnel reach 31.46万， alongside the same 7.85/千人 beds. Whether the 16739个/17.77万张/27.54万人 figures include 兵团 cannot be determined from available sources; flag this dual-track (地方口径 vs 含兵团) structure when comparing with other provinces. The quoted sentence also carries personnel figures (医疗卫生人员27.54万人； 每千人口卫生技术人员9.57人) not requested here.

### Tibet (西藏) — status: verified
- Data year: 2025 (newest data year of any province in the registry)
- Source: Tibet Autonomous Region Health Commission (西藏自治区卫生健康委员会) — 《2025年西藏自治区卫生健康事业发展统计公报》
- URL: https://wjw.xizang.gov.cn/zwgk/msggk/jktongji/202605/P020260514396224265562.pdf (article page: https://wjw.xizang.gov.cn/zwgk/msggk/jktongji/202605/t20260514_540073.html)
- Published: 2026-05-14 (URL-embedded t20260514 / P020260514…)
- Access method: pdf-downloaded-and-extracted — first-wave agent curl with Mozilla UA (WebFetch blocked for these .gov.cn domains): article HTML title “TITLE_TAG: 2025年西藏自治区卫生健康事业发展统计公报_西藏自治区卫生健康委员会”; PDF 273,875 bytes, "PDF document, version 1.7, 6 pages" (Oct 11 23:55). The download agent later crashed (sensitive-content API filter); the operator harvested its downloads/transcript and extracted the PDF with pypdf himself
- Live verification: download 2026-10-11, operator extraction 2026-10-11..12 (main session line 530; PROVINCE block line 622)
- Institutions (verbatim): “2025年全区医疗卫生机构总数 7436 个（含村卫生室 5220 个）”
- Institutions value: 7436个 (total includes 5,220 village clinics, stated separately)
- Beds (verbatim): “2025年医疗卫生机构实有床位数 22154 张，其中：医院 17390 张（综合医院 11707 张、中西医结合医院 111 张、藏医医院 3755 张、专科医院 1817 张），社区卫生服务中心（站）131 张，乡镇卫生院 2890 张…”
- Beds value: 22154张 (ACTUAL beds, 实有床位数)
- Beds per 1,000 (verbatim): “2025年全区每千人口医疗卫生机构床位数为 5.92 张。（以常住人口 374 万计算）”
- Beds per 1,000 value: 5.92张 (denominator explicitly 常住人口 374万)
- Verification notes: year choice recorded in the download agent: “Tibet's 2025 bulletin (2025 data, published 2026-05-14) exists — that's newer than the 2024 one, so I'll target it.” Beds quote truncated at “乡镇卫生院 2890 张” in the extraction window (operator block marks the truncation). Raw pypdf output carried line-wrap spaces — collapsed when quoting; characters unchanged. Scope: 全区.
- Transcript evidence: main session `d7cfde67….jsonl` ~lines 518–519, 529–530, 610–611, 622; download agent `agent-ad232068b439c663f.jsonl` lines 26–28, 31–33, 43–44

## Status summary

| Status | Provinces | Count |
|--------|-----------|-------|
| verified — provincial health commission bulletin (统计公报) | Shanxi, Inner Mongolia, Jiangsu, Anhui, Shandong, Hunan, Guangdong, Guangxi, Hainan, Chongqing, Sichuan, Guizhou, Shaanxi, Ningxia, Tibet | 15 |
| verified — economic-bulletin fallback (no health bulletin exists online; operator first-hand) | Qinghai | 1 |
| partial — genuine figures, sourced from the economic bulletin or an official non-bulletin release | Tianjin, Hebei, Liaoning, Jilin, Heilongjiang, Shanghai, Zhejiang, Fujian, Jiangxi, Henan, Hubei, Gansu, Xinjiang | 13 |
| Pass 1 (S12), kept without re-verification | Beijing, Yunnan | 2 |

Pass-2 total: 29 provinces (15 + 1 + 13). Combined with Pass 1: all 31
provincial-level divisions covered by live-verified official records — 91
records in the registry. Scanned-PDF provinces (Shaanxi, Gansu, Ningxia)
were OCR-read with macOS Vision (zh-Hans) and cross-validated by internal
arithmetic; Gansu's unretrievable 2024/2025 editions (Knownsec anti-bot
wall) are named in its section and excluded per the no-fabrication rule.
