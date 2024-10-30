import { defineConfig } from 'vitepress';
import {
  pagefindPlugin,
  chineseSearchOptimize,
} from 'vitepress-plugin-pagefind';

// https://vitepress.dev/reference/site-config
export default defineConfig({
  lang: 'zh-CN',
  title: 'Embykeeper',
  description: 'Emby 签到保号的自动执行工具',
  cleanUrls: true,
  head: [['link', { rel: 'icon', href: '/favicon.ico' }]],
  sitemap: {
    hostname: 'https://emby-keeper.github.io',
  },
  vite: {
    plugins: [
      pagefindPlugin({
        customSearchQuery: chineseSearchOptimize,
        btnPlaceholder: '搜索',
        placeholder: '搜索文档',
        emptyText: '空空如也',
        heading: '共: {{searchResult}} 条结果',
        excludeSelector: ['img', 'a.header-anchor'],
      }),
    ],
  },
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: '/logo.svg',
    footer: {
      message: 'Released under the GPLv3 License.',
      copyright: 'Copyright © 2024',
    },

    nav: [
      { text: '首页', link: '/' },
      { text: '教程', link: '/guide' },
    ],

    sidebar: [
      {
        text: '开始使用',
        items: [
          { text: '🏡 什么是 Embykeeper?', link: '/guide/' },
          { text: '🎬 支持的站点', link: '/guide/支持的站点' },
          { text: '🚀 安装指南', link: '/guide/安装指南' },
          {
            text: '🐧 Linux 安装',
            collapsed: true,
            items: [
              { text: '🐳 Docker 部署', link: '/guide/Linux-Docker-部署' },
              {
                text: '📚 Docker Compose 部署',
                link: '/guide/Linux-Docker-Compose-部署',
              },
              { text: '🏗️ 从源码构建', link: '/guide/Linux-从源码构建' },
              { text: '📦 PyPI 安装', link: '/guide/Linux-从-PyPI-安装' },
            ],
          },
          {
            text: '💻 Windows 安装',
            collapsed: true,
            items: [
              { text: '⌨️ 自动安装脚本', link: '/guide/Windows-通过脚本安装' },
              { text: '🖱️ 安装包', link: '/guide/Windows-通过安装包安装' },
            ],
          },
          { text: '🪐 在线部署', link: '/guide/在线部署' },
          { text: '❔ 常见问题', link: '/guide/常见问题' },
        ],
      },
      {
        text: '功能配置',
        items: [
          {
            text: '💡 功能说明',
            collapsed: true,
            items: [
              { text: '🎬 自动保活', link: '/guide/功能说明-自动保活' },
              { text: '📅 每日签到', link: '/guide/功能说明-每日签到' },
              { text: '👀 群组监控', link: '/guide/功能说明-群组监控' },
              { text: '💬 自动水群', link: '/guide/功能说明-自动水群' },
              { text: '📝 考核辅助', link: '/guide/功能说明-考核辅助' },
              { text: '🔔 日志推送', link: '/guide/功能说明-日志推送' },
            ],
          },
          { text: '🔧 配置文件', link: '/guide/配置文件' },
          { text: '⌨️ 命令行参数', link: '/guide/命令行参数' },
          { text: '👑 高级用户', link: '/guide/高级用户' },
        ],
      },
      {
        text: '关于开发',
        items: [
          { text: '🤝 参与开发', link: '/guide/参与开发' },
          { text: '🛠️ 调试工具', link: '/guide/调试工具' },
          { text: '⚖️ 许可', link: '/guide/许可' },
          { text: '🏭 发布周期', link: '/guide/发布周期' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/emby-keeper/emby-keeper' },
    ],

    editLink: {
      pattern: 'https://github.com/emby-keeper/emby-keeper/edit/main/docs/:path',
    },
  },
});
