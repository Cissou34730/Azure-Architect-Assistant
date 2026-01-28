import { RefObject, useEffect, useCallback } from "react";

interface UseClickOutsideProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  dropdownRef: RefObject<HTMLDivElement | null>;
  searchInputRef: RefObject<HTMLInputElement | null>;
}

export function useClickOutside({
  isOpen,
  setIsOpen,
  dropdownRef,
  searchInputRef,
}: UseClickOutsideProps) {
  const handleClickOutside = useCallback(
    (event: MouseEvent) => {
      const { target } = event;
      if (
        dropdownRef.current !== null &&
        target instanceof Node &&
        !dropdownRef.current.contains(target)
      ) {
        setIsOpen(false);
      }
    },
    [dropdownRef, setIsOpen],
  );

  useEffect(() => {
    if (!isOpen) return;

    document.addEventListener("mousedown", handleClickOutside);
    const timer = setTimeout(() => {
      searchInputRef.current?.focus();
    }, 100);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      clearTimeout(timer);
    };
  }, [isOpen, handleClickOutside, searchInputRef]);
}
