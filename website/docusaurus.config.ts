import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const app_name: string = 'enterprise_ai_governance_add-on_for_splunk'.replaceAll("_", " ");
const repo_name: string = 'enterprise_ai_governance_add-on_for_splunk';
const app_descr: string = 'Collects and normalizes audit, identity, usage, cost, and health data from enterprise AI platforms so teams can monitor security, compliance, adoption, spend, and operational risk in Splunk.';

const config: Config = {
  title: app_name,
  tagline: app_descr,
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://splunk-platform-apps.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/' + repo_name + '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'splunk-platform-apps', // Usually your GitHub org/user name.
  projectName: repo_name,
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts'
        },
        theme: {
          customCss: ['./src/css/custom.css', './src/css/fonts.css']
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Documentation',
      logo: {
        alt: 'Splunk Logo',
        src: 'img/logo.svg',
        srcDark: 'img/logo-dark.svg',
      },
      items: [
        {
          to: '/',
          label: 'Home',
          position: 'left',
          activeBaseRegex: '^/' + repo_name + '/?$',
        },
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://github.com/splunk-platform-apps/' + repo_name + '/issues',
          position: 'left',
          label: 'Known Issues',
          'aria-label': 'Known Issues',
        },
        {
          href: 'https://github.com/splunk-platform-apps/' + repo_name,
          position: 'right',
          className: 'header-github-link',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      logo: {
        srcDark: 'img/devrel-logo-dark.png',
        src: 'img/devrel-logo-light.png',
        alt: 'Splunk DevRel logo',
        height: 32
      },
      links: [
        {
          items: [
            {
              label: 'Community Slack',
              href: 'https://splunkcommunity.slack.com/archives/C04DC8JJ6',
              className: 'footer-row-primary'
            },
            {
              label: 'Splunk Dev',
              href: 'https://dev.splunk.com/',
              className: 'footer-row-primary'
            },
            {
              label: 'Contact',
              href: 'mailto:devinfo@splunk.com',
              className: 'footer-row-primary'
            }
          ],
        },
        {
          items: [
            { label: 'Legal', href: 'https://www.splunk.com/en_us/legal.html', className: 'footer-row-secondary' },
            { label: 'Patents', href: 'https://www.splunk.com/en_us/legal/patents.html', className: 'footer-row-secondary' },
            { label: 'Privacy', href: 'https://www.splunk.com/en_us/legal/privacy-policy.html?301=/en_us/legal/privacy/privacy-policy.html', className: 'footer-row-secondary' }
          ],
        },
      ],
      copyright: `© 2025 - ${new Date().getFullYear()} Splunk LLC All rights reserved.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
