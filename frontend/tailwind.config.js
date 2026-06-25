/** @type {import('tailwindcss').Config} */
// Carbon 디자인 토큰 (시안 HTML의 tailwind.config 그대로 옮김). 색/폰트의 단일 출처.
export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["General Sans", "Pretendard", "system-ui", "sans-serif"],
        sans: ["Pretendard", "General Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        ink: { DEFAULT: "#08080A", 800: "#0C0C0F", 700: "#101014", 600: "#16161B" },
        line: "rgba(255,255,255,0.07)",
        lineHover: "rgba(255,255,255,0.16)",
        fg: { DEFAULT: "#ECEDF1", muted: "#8C8F99", faint: "#80838F" },
        gold: { DEFAULT: "#E6B566", soft: "#F0CB8C", deep: "#C99749" },
        danger: "#E0796B",
      },
      letterSpacing: { tightest: "-0.04em" },
    },
  },
  plugins: [],
};
