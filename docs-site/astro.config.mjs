// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import remarkMermaid from 'remark-mermaidjs';

export default defineConfig({
	site: 'https://mizphses.github.io',
	base: '/millicall-pbx',
	markdown: {
		remarkPlugins: [remarkMermaid],
	},
	integrations: [
		starlight({
			title: 'Millicall PBX',
			defaultLocale: 'root',
			locales: {
				root: { label: '日本語', lang: 'ja' },
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/mizphses/millicall' }],
			sidebar: [
				{
					label: 'はじめに',
					items: [
						{ label: '概要', slug: 'guides/overview' },
						{ label: 'クイックスタート', slug: 'guides/quickstart' },
					],
				},
				{
					label: 'セットアップ',
					items: [
						{ label: 'インストール', slug: 'setup/install' },
						{ label: '環境変数', slug: 'setup/env' },
						{ label: 'Cloudflare Tunnel', slug: 'setup/tunnel' },
						{ label: 'ファイアウォール', slug: 'setup/firewall' },
						{ label: '電話機ネットワーク', slug: 'setup/network' },
					],
				},
				{
					label: '使い方',
					items: [
						{ label: 'ダッシュボード', slug: 'usage/dashboard' },
						{ label: '内線アカウント', slug: 'usage/extensions' },
						{ label: 'SIP電話機', slug: 'usage/peers' },
						{ label: '外線トランク', slug: 'usage/trunks' },
						{ label: 'ワークフロー', slug: 'usage/workflows' },
						{ label: 'デバイス管理', slug: 'usage/devices' },
						{ label: 'プロビジョニング', slug: 'usage/provisioning' },
					],
				},
				{
					label: 'アーキテクチャ',
					items: [
						{ label: 'システム構成', slug: 'architecture/overview' },
						{ label: 'セキュリティ', slug: 'architecture/security' },
					],
				},
			],
		}),
	],
});
