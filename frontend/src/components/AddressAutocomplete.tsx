import { useEffect, useMemo, useRef, useState } from "react";
import type { GeocodeSuggestion } from "../types";
import { fetchGeocodeSuggestions } from "../api/client";

interface Props {
  label: string;
  value: string;
  placeholder?: string;
  onValueChange: (value: string) => void;
  onSelectSuggestion: (suggestion: GeocodeSuggestion) => void;
}

export default function AddressAutocomplete({
  label,
  value,
  placeholder,
  onValueChange,
  onSelectSuggestion,
}: Props) {
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    const query = value.trim();
    if (query.length < 3) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const results = await fetchGeocodeSuggestions(query);
        if (!cancelled) {
          setSuggestions(results);
          setOpen(results.length > 0);
        }
      } catch {
        if (!cancelled) {
          setSuggestions([]);
          setOpen(false);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [value]);

  const hintText = useMemo(() => {
    if (loading) return "Searching...";
    if (!value || value.trim().length < 3) return "Type at least 3 characters.";
    if (!open || suggestions.length === 0) return "No suggestions found.";
    return `${suggestions.length} suggestions`;
  }, [loading, open, suggestions.length, value]);

  return (
    <div className="field autocomplete-field" ref={containerRef}>
      <label>{label}</label>
      <div className="input-with-icon">
        <span className="input-icon" aria-hidden="true">⌕</span>
        <input
          value={value}
          placeholder={placeholder}
          onChange={(e) => {
            onValueChange(e.target.value);
            setOpen(true);
          }}
          aria-label={label}
        />
      </div>
      <span className="field-hint">{hintText}</span>
      {open && suggestions.length > 0 && (
        <div className="autocomplete-list">
          {suggestions.map((suggestion) => (
            <button
              className="autocomplete-item"
              key={`${suggestion.lat}-${suggestion.lon}-${suggestion.display_name}`}
              onClick={() => {
                onValueChange(suggestion.display_name);
                onSelectSuggestion(suggestion);
                setOpen(false);
              }}
              type="button"
            >
              {suggestion.display_name}
            </button>
          ))}
        </div>
      )}
      {open && !loading && value.trim().length >= 3 && suggestions.length === 0 && (
        <div className="autocomplete-empty" role="status" aria-live="polite">
          No matching locations found.
        </div>
      )}
    </div>
  );
}
