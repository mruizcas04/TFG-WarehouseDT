export function formatLocation(loc, placeholder = null) {
  if (!loc) return placeholder;
  const parts = [];
  if (loc.aisle_number != null) parts.push(`Pasillo ${loc.aisle_number}`);
  if (loc.shelf_number != null) parts.push(`Est. ${loc.shelf_number}`);
  if (loc.level_number != null) parts.push(`Balda ${loc.level_number}`);
  parts.push(`Hueco ${loc.position_number}`);
  return parts.join(' · ');
}
