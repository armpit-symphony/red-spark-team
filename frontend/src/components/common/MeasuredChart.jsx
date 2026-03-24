import { useEffect, useRef, useState } from 'react';

export const MeasuredChart = ({ children, testId }) => {
  const containerRef = useRef(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return undefined;
    }

    const updateSize = () => setWidth(Math.max(element.getBoundingClientRect().width - 2, 0));
    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="chart-shell" data-testid={testId}>
      {width > 0 ? children({ width, height: 300 }) : null}
    </div>
  );
};
