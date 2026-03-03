
interface ProgressBarProps {
    progress: number;
    className?: string;
}

export default function ProgressBar({ progress, className = "" }: ProgressBarProps) {
    return (
        <div className={`w-full bg-gray-200 rounded-full h-2.5 overflow-hidden ${className}`}>
            <div
                className="bg-[#5697B0] h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
            ></div>
        </div>
    );
}
