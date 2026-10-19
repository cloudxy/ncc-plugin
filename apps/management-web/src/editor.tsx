import { useEffect, useRef } from "react";
import { EditorView } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { markdown } from "@codemirror/lang-markdown";
import { basicSetup } from "codemirror";

export function TextEditor({
  value,
  onChange,
  onSelection,
  readOnly = false,
  height = 420,
}: {
  value: string;
  onChange?: (value: string) => void;
  onSelection?: (from: number, to: number) => void;
  readOnly?: boolean;
  height?: number;
}) {
  const element = useRef<HTMLDivElement>(null),
    editor = useRef<EditorView | null>(null),
    handler = useRef(onChange);
  handler.current = onChange;
  const selecting = useRef(onSelection),
    programmatic = useRef(false);
  selecting.current = onSelection;
  useEffect(() => {
    if (!element.current) return;
    const view = new EditorView({
      parent: element.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          markdown(),
          EditorView.lineWrapping,
          EditorState.readOnly.of(readOnly),
          EditorView.editable.of(!readOnly),
          EditorView.theme({
            "&": { height: `${height}px`, fontSize: "16px" },
            ".cm-content": {
              fontFamily: 'Georgia,"Songti SC",serif',
              padding: "24px",
              lineHeight: "1.95",
            },
            ".cm-scroller": { overflow: "auto" },
            ".cm-gutters": { background: "#fafbf9", border: "none" },
          }),
          EditorView.updateListener.of((update) => {
            if (update.docChanged && !programmatic.current)
              handler.current?.(update.state.doc.toString());
            if (update.selectionSet) {
              const s = update.state.selection.main;
              selecting.current?.(s.from, s.to);
            }
          }),
        ],
      }),
    });
    editor.current = view;
    return () => {
      view.destroy();
      editor.current = null;
    };
  }, [readOnly, height]);
  useEffect(() => {
    const view = editor.current;
    if (view && value !== view.state.doc.toString()) {
      programmatic.current = true;
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: value },
      });
      programmatic.current = false;
    }
  }, [value]);
  return <div ref={element} className="text-editor" />;
}
