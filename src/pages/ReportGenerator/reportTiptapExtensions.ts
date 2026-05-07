import { mergeAttributes } from '@tiptap/core';
import Heading from '@tiptap/extension-heading';
import Highlight from '@tiptap/extension-highlight';

/** 保留 HTML 中的 id / data-section-id / class，供大纲锚点与样式 */
export const ReportHeading = Heading.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      id: {
        default: null,
        parseHTML: (element) => element.getAttribute('id'),
        renderHTML: (attributes) => {
          if (!attributes.id) return {};
          return { id: attributes.id as string };
        },
      },
      dataSectionId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-section-id'),
        renderHTML: (attributes) => {
          if (!attributes.dataSectionId) return {};
          return { 'data-section-id': attributes.dataSectionId as string };
        },
      },
      class: {
        default: null,
        parseHTML: (element) => element.getAttribute('class'),
        renderHTML: (attributes) => {
          if (!attributes.class) return {};
          return { class: attributes.class as string };
        },
      },
    };
  },
});

/**
 * 正文溯源：mock HTML 使用 span.highlight + data-ref；
 * 输出仍用 span，并保留 data-cite-num（角标）。
 */
export const ReportHighlight = Highlight.extend({
  addAttributes() {
    const base = this.parent?.() ?? {};
    return {
      ...base,
      ref: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-ref'),
        renderHTML: (attributes) => {
          if (!attributes.ref) return {};
          return { 'data-ref': attributes.ref as string };
        },
      },
      citeNum: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-cite-num'),
        renderHTML: (attributes) => {
          if (!attributes.citeNum) return {};
          return { 'data-cite-num': attributes.citeNum as string };
        },
      },
      title: {
        default: null,
        parseHTML: (element) => element.getAttribute('title'),
        renderHTML: (attributes) => {
          if (!attributes.title) return {};
          return { title: attributes.title as string };
        },
      },
    };
  },

  parseHTML() {
    return [
      { tag: 'mark' },
      {
        tag: 'span',
        getAttrs: (el) => {
          if (!(el instanceof HTMLElement)) return false;
          return el.classList.contains('highlight') ? null : false;
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(
        { class: 'highlight' },
        this.options.HTMLAttributes,
        HTMLAttributes,
      ),
      0,
    ];
  },
});
