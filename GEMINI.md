# キーワード縦横展開 & Ubersuggest当たり判定システム (Master Entry Point)

本ワークスペースでは、入力されたシードキーワードを起点として**「語句の数と意味のデュアル解析」**を行い、**「前後2大固定軸展開（対称性の原則）」**と**「1-Shot メガバッチAPI取得」**により、当たりキーワードを判定・レポート出力します。

保守・修正を容易にするため、各責務ごとにルールファイルを1責務1ファイルに分割管理しています。

---

## 1. 発動トリガー
* ユーザーが「〇〇 〇〇」「〇〇 〇〇 〇〇」「リサーチ：〇〇」「展開：〇〇」のようにキーワードを入力した際、自動適用する。

---

## 2. 分割ルールファイル群（単一責任モジュール）

各処理ステップの詳細仕様は、以下の単一責任ルールファイルに定義されています。修正・保守時は該当ファイルを参照・更新してください。

| ルールID | ルールファイル名 | 責任範囲・主な内容 |
| :--- | :--- | :--- |
| **Rule 01** | [rules/rule_01_syntax_analysis.md](file:///c:/Users/user/OneDrive/prideall/projects/wide/rules/rule_01_syntax_analysis.md) | **構文解析**: 語句の数（構造）と意味（本質）のデュアル解析原則、2語・3語パターンの特定。 |
| **Rule 02** | [rules/rule_02_fixed_expansion.md](file:///c:/Users/user/OneDrive/prideall/projects/wide/rules/rule_02_fixed_expansion.md) | **固定展開**: 前後2大固定軸展開（`[A] 〇〇` と `〇〇 [B]`）、完全対称性の原則、安易な3語化の禁止。 |
| **Rule 03** | [rules/rule_03_pre_output_validation.md](file:///c:/Users/user/OneDrive/prideall/projects/wide/rules/rule_03_pre_output_validation.md) | **バリデーション**: 出力直前にAIが自律検証する必須チェックリスト（語数・対称性・主従バイアス・25件閾値）。 |
| **Rule 04** | [rules/rule_04_ubersuggest_megabatch.md](file:///c:/Users/user/OneDrive/prideall/projects/wide/rules/rule_04_ubersuggest_megabatch.md) | **API取得仕様**: 25件未満APIコール抑止原則（不足時ユーザー報告）、1コール完結メガバッチフロー、枯渇検知、推定数値厳禁。 |
| **Rule 05** | [rules/rule_05_multi_tier_cache.md](file:///c:/Users/user/OneDrive/prideall/projects/wide/rules/rule_05_multi_tier_cache.md) | **多層キャッシュ**: Tier 1マスターDB/生ログ/CSV、Tier 2高速KeyValue、PowerShell Pure ASCII規約。 |
| **Rule 06** | [rules/rule_06_output_format.md](file:///c:/Users/user/OneDrive/prideall/projects/wide/rules/rule_06_output_format.md) | **出力フォーマット**: 回答時の必須5セクション構成（構文解析、軸①、軸②、リサーチテーブル、戦略アドバイス）。 |

---

## 3. スクリプト構成リファレンス（命名規則: カテゴリ_機能.ps1）

| カテゴリ | スクリプトファイル名 | 役割・機能 |
| :--- | :--- | :--- |
| **`workflow_`** | [workflow_keyword_pipeline.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/workflow_keyword_pipeline.ps1) | **マスター統合パイプライン**: 構文解析 ➡ 展開 ➡ 閾値検証 ➡ (対話補完) ➡ 1-Shot検索 ➡ レポート出力を一気通貫実行。 |
| **`syntax_`** | [syntax_keyword_analyzer.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/syntax_keyword_analyzer.ps1) | **構文解析**: 空白正規化、語数判定（2語/3語）、スロット分解（A, B, C）。 |
| **`expansion_`** | [expansion_keyword_builder.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/expansion_keyword_builder.ps1) | **固定軸展開**: 前後2大固定軸（`[A] 〇〇` と `〇〇 [B]`）リスト生成・外部候補統合。 |
| **`validator_`** | [validator_keyword_threshold.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/validator_keyword_threshold.ps1) | **バリデーション**: 対称性検証および**25件閾値チェック**（不足数算出）。 |
| **`ui_`** | [ui_interactive_prompter.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/ui_interactive_prompter.ps1) | **対話補完UI**: 25件未満時に「現在〇個/不足△個」を色付き表示し追加KWを受付。 |
| **`engine_`** | [engine_keyword_search.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/engine_keyword_search.ps1) | **1-Shot検索エンジン**: キャッシュ差分照合、合体配列1回コール、多層保存、星判定。 |
| **`api_`** | [api_ubersuggest_client.ps1](file:///c:/Users/user/OneDrive/prideall/projects/wide/api_ubersuggest_client.ps1) | **APIブリッジ**: Ubersuggest MCPクライアント（JSON-RPC 2.0、生ログ監査、枯渇検知）。 |
| **`reporter_`** | [reporter_markdown_output.ps1](file:///c:/Users/santa/OneDrive/prideall/projects/wide/reporter_markdown_output.ps1) | **レポート生成**: ルール06準拠の5セクション構成Markdown生成・ファイル保存。 |
| **`db_`** | [db_keyword_manager.ps1](file:///c:/Users/santa/OneDrive/prideall/projects/wide/db_keyword_manager.ps1) | **DB管理CLI**: データベース一覧表示、星別キーワード抽出、CSV同期。 |
| **`sync_`** | [sync_wide_pipeline.ps1](file:///c:/Users/santa/OneDrive/prideall/projects/wide/sync_wide_pipeline.ps1) | **双方向同期＆GitHubプッシャー**: wideとwide-オンデマンドの差分検知、自動コミット＆GitHubプッシュ。 |

### Python・Sidecar展開エンジン（1ファイル1責務モジュール構成）

| モジュール名 | 役割・責務 |
| :--- | :--- |
| **`api_suggest_client.py`** | **外部サジェストAPI通信**: GoogleサジェストAPI等との通信・クエリ候補取得専用。 |
| **`filter_prohibited_terms.py`** | **禁止語事前排除判定**: 全国の自治体名（3,756件マスター照合）、地元・店舗・売り場系単語、エンタメ系単語の排除判定専用。 |
| **`engine_semantic_family.py`** | **同族・スケール判定エンジン**: 数値スケール単位（号数・合数・年代等）の正規表現動的生成、ドメイン意味属性（色・スイーツ・主食・家電等）の同族検出専用。 |
| **`generator_ai_expansion.py`** | **固定軸展開オーケストレーター**: 上記3モジュールを結合し、軸①（前固定25個）・軸②（後固定25個）の組み立て・25個閾値制御を実行。 |
| **`engine_star_evaluator.py`** | **SERP星判定エンジン**: SERP生データから個人ブログ・知恵袋のドメインを照合し星判定（★3〜★0）を算出。 |
| **`batch_research_worker.py`** | **メガバッチ実行ワーカー**: 二段階スクリーニング（星0はAPIスキップ）とUbersuggestメガバッチ取得を実行。 |

---

## 4. データストア構成

* **Tier 1 (生データ監査)**: `raw_api_archive.json`（未加工JSON全件タイムスタンプ保存）
* **Tier 1 (マスターDB)**: `keywords_db.json`（構造化マスターDB）
* **Tier 1 (一覧閲覧用)**: `keywords.csv`（Excel等で閲覧可能なCSV）
* **Tier 2 (高速キャッシュ)**: `verified_volume_cache.json`（超高速KeyValueストア・API消費0保証）

---

## 5. 【絶対規約】ボリューム値の実測厳格原則（推定・捏造の完全根絶）

> [!CAUTION]
> **【AIによる推測値・固定値・サンプル値の代入は永久禁止】**
> * 検索ボリューム（Vol）および難易度（SD）は、**Ubersuggest公式APIが返却した実測生データ（または生データ監査済みのverified_volume_cache.json）以外の数値を一切認めてはならない**。
> * API制限（HTTP 403/429、日次枠枯渇など）で新規データが取得できない場合、AIが「一般的な相場」「推測値」「辞書マッピング」「サンプル値」を捏造・代入してはならず、**必ず正直に「N/A」または「未取得（API上限）」と出力すること**。
> * ユーザーに提供する価値の源泉は「生の事実データ」であり、数値の捏造はシステム全体の信頼性を損なう重大な違反とする。

---

## 6. 【絶対規約】地元系KW・エンタメ系KWの事前完全排除原則

> [!IMPORTANT]
> **【軸生成・キーワード展開時の事前フィルタリング徹底】**
> * **地元系（地域・場所・店舗）**: 都道府県・市区町村・駅名、`近く`, `周辺`, `店舗`, `売り場`, `どこで買える` などの場所系単語は、Googleマップ（MEO）や大手ポータルに上位を独占され星0確定となるため、**軸生成段階で100%排除**すること。
> * **エンタメ系（芸能・アニメ・ゲーム・動画等）**: 芸能人名、`アニメ`, `漫画`, `声優`, `キャラ`, `ゲーム攻略`, `曲`, `歌詞`, `動画`, `ファン` などのエンタメ単語は、公式サイト・SNS独占およびトレンド乱高下により星が安定しないため、**軸生成段階で100%排除**すること。
> * **個人ブログ優遇**: 軸の中心は常に「知恵袋・個人ブログが居座る悩み・トラブル防止・代用・手順・不安解消系」に集中させること。
