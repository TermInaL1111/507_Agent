import { mockCampusLocations } from '../data/campusLocations';

const unwrapLocations = (payload) => payload?.data?.locations || payload?.locations || [];

export const fetchCampusLocations = async () => {
  try {
    const response = await fetch('/api/campus/locations');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const locations = unwrapLocations(payload);
    return locations.length ? locations : mockCampusLocations;
  } catch (error) {
    console.warn('校园地点接口不可用，使用本地 mock 数据:', error);
    return mockCampusLocations;
  }
};

export const searchCampusLocations = (locations, keyword, type = 'all') => {
  const normalized = keyword.trim().toLowerCase();
  return locations.filter((location) => {
    const typeMatched = type === 'all' || location.type === type;
    if (!typeMatched) return false;
    if (!normalized) return true;

    const fields = [
      location.name,
      location.type,
      location.address,
      location.description,
      ...(location.aliases || []),
      ...(location.tags || [])
    ];
    return fields.some((item) => String(item || '').toLowerCase().includes(normalized));
  });
};

export const isRenderableLocation = (location) => {
  return Number.isFinite(Number(location?.longitude)) && Number.isFinite(Number(location?.latitude));
};

export const fetchWalkingRoute = async ({ fromId, toId, origin, destination, originName, destinationName }) => {
  const params = new URLSearchParams();
  if (fromId) params.set('from_id', fromId);
  if (toId) params.set('to_id', toId);
  if (origin) params.set('origin', origin);
  if (destination) params.set('destination', destination);
  if (originName) params.set('origin_name', originName);
  if (destinationName) params.set('destination_name', destinationName);

  const response = await fetch(`/api/campus/route/walking?${params.toString()}`);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.detail || `路线规划失败：HTTP ${response.status}`);
  }
  return payload?.data?.route || payload?.route;
};
