export function Banner() {
  const bannerMessage = import.meta.env.VITE_BANNER_MESSAGE;

  if (bannerMessage === undefined || bannerMessage === "") {
    return null;
  }

  return (
    <div className="bg-yellow-400 border-b-2 border-yellow-600 px-4 py-2 text-center font-semibold text-yellow-900 shadow-md">
      {bannerMessage}
    </div>
  );
}
