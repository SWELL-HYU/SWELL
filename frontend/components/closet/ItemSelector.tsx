import React from "react";
import type { ClosetItem } from "@/lib/closet";

interface ItemSelectorProps {
    isOpen: boolean;
    onClose: () => void;
    category: string;
    items: ClosetItem[];
    onSelect: (item: ClosetItem) => void;
}

export default function ItemSelector({
    isOpen,
    onClose,
    category,
    items,
    onSelect,
}: ItemSelectorProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Modal / Bottom Sheet */}
            <div className="relative bg-white w-full max-w-lg sm:rounded-2xl rounded-t-2xl shadow-2xl max-h-[80vh] flex flex-col animate-slideUp">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b">
                    <h3 className="text-lg font-bold text-gray-800">
                        {category} 선택
                    </h3>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-full transition"
                    >
                        ✕
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {items.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-10 text-gray-400">
                            <span className="text-4xl mb-2">📦</span>
                            <p>저장된 {category} 아이템이 없습니다</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-3 gap-3">
                            {items.map((item) => (
                                <div
                                    key={item.id}
                                    onClick={() => onSelect(item)}
                                    className="cursor-pointer group relative aspect-square bg-gray-50 rounded-xl overflow-hidden border border-gray-100 hover:border-[#5697B0] transition-all"
                                >
                                    {item.imageUrl ? (
                                        <img
                                            src={item.imageUrl}
                                            alt={item.name}
                                            className="w-full h-full object-cover"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center">
                                            <span className="text-2xl text-gray-300">👕</span>
                                        </div>
                                    )}

                                    {/* Name Overlay */}
                                    <div className="absolute inset-x-0 bottom-0 bg-black/50 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <p className="text-white text-xs truncate">{item.name}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
