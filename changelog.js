// 由 tools/gen_changelog.py 生成，请勿手改。
// 源：trader-android 的 git log。重新生成：python3 tools/gen_changelog.py
window.CHANGELOG = {
  "source": "trader-android",
  "updatedThrough": "2026-09-24 22:24",
  "entries": [
    {
      "date": "2026-09-24",
      "items": [
        {
          "tag": "对齐 iOS",
          "text": "价格轴压窄到 46、金额补 ¥ 与千分位、档位手数把手续费算进预算"
        },
        {
          "tag": "",
          "text": "CI: release.sh 显式把 APK 路径传给 build.sh"
        }
      ]
    },
    {
      "date": "2026-09-21",
      "items": [
        {
          "tag": "",
          "text": "CI: 提交/合并到 main 后自动打包 APK 并刷新落地页"
        }
      ]
    },
    {
      "date": "2026-09-20",
      "items": [
        {
          "tag": "档位行 / 平仓行",
          "text": "手数框与比例按钮改成显式等高"
        },
        {
          "tag": "平仓弹窗",
          "text": "比例按钮挪到头部同一行，输入框缩小"
        }
      ]
    },
    {
      "date": "2026-09-19",
      "items": [
        {
          "tag": "平仓弹窗",
          "text": "输入框只接手数 + 百分比快捷按钮组"
        },
        {
          "tag": "",
          "text": "反向开仓提示改成「先平仓后才能…」"
        },
        {
          "tag": "",
          "text": "平仓弹窗内填数量/比例，反向开仓按钮置灰但仍可点"
        },
        {
          "tag": "",
          "text": "按 iOS 设计全面对齐 + release 签名包"
        }
      ]
    },
    {
      "date": "2026-09-17",
      "items": [
        {
          "tag": "",
          "text": "修两个只有真机/模拟器才暴露的 bug（价格轴被切、下一天闪退）"
        }
      ]
    },
    {
      "date": "2026-09-16",
      "items": [
        {
          "tag": "",
          "text": "交易训练台 Android 原生版首版"
        }
      ]
    }
  ]
};
