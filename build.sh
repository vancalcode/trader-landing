#!/usr/bin/env bash
#
# 把 trader-android 的 release APK 同步到落地页，并刷新 meta.js。
#
#   ./build.sh                 # 取默认构建产物
#   ./build.sh /path/to.apk    # 指定 APK
#
# 页面上的版本 / 大小 / 更新时间 / SHA-256 全部由 meta.js 驱动，
# 所以 APK 重新打包之后**必须**跑一次，否则页面上的数字会说谎。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APK_SRC="${1:-$HERE/../trader-android/app/build/outputs/apk/release/app-release.apk}"

[ -f "$APK_SRC" ] || { echo "找不到 APK：$APK_SRC" >&2; exit 1; }

# -p 必须带：否则 cp 会把目标文件的 mtime 改成「现在」，
# 页面上的「更新时间」就变成了同步时刻，而不是真正的打包时刻。
cp -p "$APK_SRC" "$HERE/app-release.apk"

python3 - "$HERE/app-release.apk" "$(dirname "$APK_SRC")/output-metadata.json" "$HERE/meta.js" <<'PY'
import hashlib, json, os, sys, time

apk, meta_json, out = sys.argv[1], sys.argv[2], sys.argv[3]

version_name, version_code = "1.0.0", 0
if os.path.isfile(meta_json):
    try:
        with open(meta_json, encoding="utf-8") as f:
            el = json.load(f)["elements"][0]
        version_name = el.get("versionName") or version_name
        version_code = el.get("versionCode") or 0
    except Exception as e:
        print("  ! 读 output-metadata.json 失败，退回默认版本号：%s" % e, file=sys.stderr)

size = os.path.getsize(apk)
digest = hashlib.sha256()
with open(apk, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        digest.update(chunk)

meta = {
    "versionName": version_name,
    "versionCode": version_code,
    "size": size,
    "sizeText": "%.1f MB" % (size / 1048576.0),
    "sha256": digest.hexdigest(),
    "builtAt": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(apk))),
}

with open(out, "w", encoding="utf-8") as f:
    f.write("// 由 build.sh 生成，请勿手改。\nwindow.APP_META = {\n")
    for k, v in meta.items():
        f.write("  %s: %s,\n" % (json.dumps(k), json.dumps(v, ensure_ascii=False)))
    f.write("};\n")

print("  APK     %s（%s 字节）" % (meta["sizeText"], meta["size"]))
print("  版本    %s（versionCode %s）" % (meta["versionName"], meta["versionCode"]))
print("  打包于  %s" % meta["builtAt"])
print("  SHA-256 %s" % meta["sha256"])
PY

# ── 更新日志 + K 线图 ────────────────────────────────────────────────
# 两个都是从 App 仓库派生的，跑不动也不该拦住 APK 同步 —— 沿用已有产物就行。
PY="${PYTHON:-python3}"
soft() {
  local what="$1"; shift
  "$@" || echo "  ! $what 生成失败，沿用已有的产物" >&2
}
soft "更新日志" "$PY" "$HERE/tools/gen_changelog.py" --out "$HERE/changelog.js"
soft "K 线图（宽）" "$PY" "$HERE/tools/gen_chart.py" --preset desktop --out "$HERE/chart.svg"
soft "K 线图（窄）" "$PY" "$HERE/tools/gen_chart.py" --preset mobile  --out "$HERE/chart-mobile.svg"

echo "✅ 已同步 $HERE/app-release.apk，并重写 meta.js / changelog.js / chart*.svg"
