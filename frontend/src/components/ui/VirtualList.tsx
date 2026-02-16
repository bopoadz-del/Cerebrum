import React, { useCallback, useRef, useEffect, useState } from 'react';
import { FixedSizeList, VariableSizeList, ListChildComponentProps } from 'react-window';
import { cn } from '@/lib/utils';

// Fixed size virtual list props
interface FixedVirtualListProps<T> {
  items: T[];
  itemHeight: number;
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  height?: number | string;
  width?: number | string;
  className?: string;
  overscanCount?: number;
  onScroll?: (scrollOffset: number) => void;
  onItemsRendered?: (props: {
    overscanStartIndex: number;
    overscanStopIndex: number;
    visibleStartIndex: number;
    visibleStopIndex: number;
  }) => void;
}

// Variable size virtual list props
interface VariableVirtualListProps<T> extends Omit<FixedVirtualListProps<T>, 'itemHeight'> {
  itemSize: (index: number) => number;
  estimatedItemSize: number;
}

// Fixed size virtual list
export const FixedVirtualList = <T,>({
  items,
  itemHeight,
  renderItem,
  height = 400,
  width = '100%',
  className,
  overscanCount = 5,
  onScroll,
  onItemsRendered,
}: FixedVirtualListProps<T>) => {
  const listRef = useRef<FixedSizeList>(null);

  const ItemRenderer = useCallback(
    ({ index, style }: ListChildComponentProps) => {
      const item = items[index];
      if (!item) return null;
      return (
        <div style={style} className="w-full">
          {renderItem(item, index, style)}
        </div>
      );
    },
    [items, renderItem]
  );

  return (
    <FixedSizeList
      ref={listRef}
      height={typeof height === 'string' ? parseInt(height, 10) || 400 : height}
      itemCount={items.length}
      itemSize={itemHeight}
      width={width}
      className={cn('overflow-auto', className)}
      overscanCount={overscanCount}
      onScroll={onScroll ? ({ scrollOffset }) => onScroll(scrollOffset) : undefined}
      onItemsRendered={onItemsRendered}
    >
      {ItemRenderer}
    </FixedSizeList>
  );
};

// Variable size virtual list
export const VariableVirtualList = <T,>({
  items,
  itemSize,
  estimatedItemSize,
  renderItem,
  height = 400,
  width = '100%',
  className,
  overscanCount = 5,
  onScroll,
  onItemsRendered,
}: VariableVirtualListProps<T>) => {
  const listRef = useRef<VariableSizeList>(null);

  const ItemRenderer = useCallback(
    ({ index, style }: ListChildComponentProps) => {
      const item = items[index];
      if (!item) return null;
      return (
        <div style={style} className="w-full">
          {renderItem(item, index, style)}
        </div>
      );
    },
    [items, renderItem]
  );

  return (
    <VariableSizeList
      ref={listRef}
      height={typeof height === 'string' ? parseInt(height, 10) || 400 : height}
      itemCount={items.length}
      itemSize={itemSize}
      width={width}
      className={cn('overflow-auto', className)}
      overscanCount={overscanCount}
      estimatedItemSize={estimatedItemSize}
      onScroll={onScroll ? ({ scrollOffset }) => onScroll(scrollOffset) : undefined}
      onItemsRendered={onItemsRendered}
    >
      {ItemRenderer}
    </VariableSizeList>
  );
};

// Auto-sizing virtual list that fills container
interface AutoSizeVirtualListProps<T> extends FixedVirtualListProps<T> {
  minHeight?: number;
}

export const AutoSizeVirtualList = <T,>({
  items,
  itemHeight,
  renderItem,
  minHeight = 200,
  className,
  ...props
}: AutoSizeVirtualListProps<T>) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(minHeight);

  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const height = containerRef.current.clientHeight;
        setContainerHeight(Math.max(height, minHeight));
      }
    };

    updateHeight();

    const resizeObserver = new ResizeObserver(updateHeight);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    window.addEventListener('resize', updateHeight);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateHeight);
    };
  }, [minHeight]);

  return (
    <div ref={containerRef} className={cn('h-full w-full', className)}>
      <FixedVirtualList
        items={items}
        itemHeight={itemHeight}
        renderItem={renderItem}
        height={containerHeight}
        {...props}
      />
    </div>
  );
};

// Virtual table for large datasets
interface VirtualTableProps<T> {
  data: T[];
  columns: Array<{
    key: keyof T | string;
    header: string;
    width?: number;
    render?: (item: T, index: number) => React.ReactNode;
  }>;
  rowHeight?: number;
  headerHeight?: number;
  height?: number;
  className?: string;
  onRowClick?: (item: T, index: number) => void;
}

export const VirtualTable = <T extends Record<string, unknown>>({
  data,
  columns,
  rowHeight = 48,
  headerHeight = 40,
  height = 400,
  className,
  onRowClick,
}: VirtualTableProps<T>) => {
  const totalWidth = columns.reduce((acc, col) => acc + (col.width || 150), 0);

  const renderRow = useCallback(
    (item: T, index: number, style: React.CSSProperties) => (
      <div
        style={{
          ...style,
          display: 'flex',
          borderBottom: '1px solid #e5e7eb',
        }}
        className={cn(
          'hover:bg-gray-50 dark:hover:bg-gray-800/50',
          onRowClick && 'cursor-pointer'
        )}
        onClick={() => onRowClick?.(item, index)}
      >
        {columns.map((column) => (
          <div
            key={String(column.key)}
            style={{ width: column.width || 150, flexShrink: 0 }}
            className="px-4 py-3 text-sm text-gray-900 dark:text-white truncate"
          >
            {column.render
              ? column.render(item, index)
              : String(item[column.key as keyof T] ?? '')}
          </div>
        ))}
      </div>
    ),
    [columns, onRowClick]
  );

  return (
    <div className={cn('border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden', className)}>
      {/* Header */}
      <div
        style={{
          height: headerHeight,
          display: 'flex',
          borderBottom: '1px solid #e5e7eb',
        }}
        className="bg-gray-50 dark:bg-gray-800/50"
      >
        {columns.map((column) => (
          <div
            key={String(column.key)}
            style={{ width: column.width || 150, flexShrink: 0 }}
            className="px-4 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
          >
            {column.header}
          </div>
        ))}
      </div>

      {/* Body */}
      <FixedVirtualList
        items={data}
        itemHeight={rowHeight}
        renderItem={renderRow}
        height={height - headerHeight}
        width={totalWidth}
      />
    </div>
  );
};

// Infinite scroll virtual list
interface InfiniteVirtualListProps<T> extends FixedVirtualListProps<T> {
  hasMore: boolean;
  onLoadMore: () => void;
  loadingComponent?: React.ReactNode;
}

export const InfiniteVirtualList = <T,>({
  items,
  hasMore,
  onLoadMore,
  loadingComponent,
  onItemsRendered,
  ...props
}: InfiniteVirtualListProps<T>) => {
  const handleItemsRendered = useCallback(
    (props: {
      overscanStartIndex: number;
      overscanStopIndex: number;
      visibleStartIndex: number;
      visibleStopIndex: number;
    }) => {
      // Load more when user scrolls near the end
      if (hasMore && props.visibleStopIndex >= items.length - 5) {
        onLoadMore();
      }

      onItemsRendered?.(props);
    },
    [hasMore, items.length, onLoadMore, onItemsRendered]
  );

  return (
    <>
      <FixedVirtualList
        items={items}
        onItemsRendered={handleItemsRendered}
        {...props}
      />
      {hasMore && loadingComponent && (
        <div className="py-4 flex justify-center">{loadingComponent}</div>
      )}
    </>
  );
};

export default FixedVirtualList;
