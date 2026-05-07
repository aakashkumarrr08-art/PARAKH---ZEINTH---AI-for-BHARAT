/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./styles/**/*.{css}"],
  theme: {
    extend: {
      colors: {
        ink: "#12263a",
        brass: "#c99b4b",
        sand: "#efe8d9",
        mist: "#cfd9e3",
        ember: "#b8523b",
        pine: "#2c6a5f"
      },
      boxShadow: {
        panel: "0 20px 60px rgba(10, 24, 39, 0.16)"
      },
      backgroundImage: {
        mesh: "radial-gradient(circle at top left, rgba(201, 155, 75, 0.18), transparent 34%), radial-gradient(circle at bottom right, rgba(23, 50, 77, 0.22), transparent 28%)"
      }
    }
  },
  plugins: []
};
