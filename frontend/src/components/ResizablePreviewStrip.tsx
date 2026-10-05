import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

const MIN_H = 120;
const MAX_VH = 0.75;
const DEFAULT_H = 260;

type Props = {
  children: ReactNode;
};

export function ResizablePreviewStrip({ children }: Props) {
  const { t } = useTranslation();
  const [height, setHeight] = useState(DEFAULT_H);
  const dragging = useRef(false);
  const startY = useRef(0);
  const startH = useRef(0);

  const onMove = useCallback((clientY: number) => {
    const maxH = Math.floor(window.innerHeight * MAX_VH);
    const delta = startY.current - clientY;
    const next = Math.min(maxH, Math.max(MIN_H, startH.current + delta));
    setHeight(next);
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      onMove(e.clientY);
    };
    const onMouseUp = () => {
      dragging.current = false;
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onMove]);

  const onHandleDown = (e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startY.current = e.clientY;
    startH.current = height;
  };

  return (
    <div className="preview-strip-resizable" style={{ height }}>
      <div
        className="preview-resize-handle"
        role="separator"
        aria-orientation="horizontal"
        aria-valuenow={height}
        onMouseDown={onHandleDown}
        title={t("preview.resizeHint")}
      />
      <div className="preview-strip-inner">{children}</div>
    </div>
  );
}
