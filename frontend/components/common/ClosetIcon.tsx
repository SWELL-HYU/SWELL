interface ClosetIconProps {
    size?: number;
    className?: string;
}

export default function ClosetIcon({ size = 24, className = "" }: ClosetIconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={className}
        >
            {/* 옷걸이 디자인 */}
            <path
                d="M12 4.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"
                fill="currentColor"
            />
            <path
                d="M12 4.5v2.25"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
            />
            <path
                d="M5 8.5l7-1.75 7 1.75"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <path
                d="M5 8.5v11.5c0 1.105.895 2 2 2h10c1.105 0 2-.895 2-2V8.5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <path
                d="M9 14h6M9 17.5h6"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
            />
        </svg>
    );
}