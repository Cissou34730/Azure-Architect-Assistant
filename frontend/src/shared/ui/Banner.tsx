export function Banner() {
  const bannerMessage = import.meta.env.VITE_BANNER_MESSAGE;

  if (bannerMessage === undefined || bannerMessage === "") {
    return null;
  }

  return (
    <div className="bg-warning border-b-2 border-warning px-4 py-2 text-center font-semibold text-warning-strong shadow-md">
      {bannerMessage}
    </div>
  );
}

