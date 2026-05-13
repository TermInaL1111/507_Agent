<template>
  <div class="campus-map-page">
    <section class="map-sidebar">
      <div class="map-title-row">
        <div>
          <h2>校园导航</h2>
          <p>搜索地点、查看详情并跳转高德步行导航</p>
        </div>
        <el-button circle :icon="Refresh" :loading="loadingLocations" @click="loadLocations" />
      </div>

      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索图书馆、吃饭、教学楼、宿舍"
        :prefix-icon="Search"
        class="search-input"
      />

      <el-segmented v-model="activeType" :options="typeOptions" class="type-filter" />

      <el-segmented v-model="activeCampus" :options="campusOptions" class="campus-filter" />

      <el-select v-model="routeStartId" clearable filterable placeholder="选择站内路线起点；留空则使用当前位置" class="route-start-select">
        <el-option
          v-for="location in locations"
          :key="location.id"
          :label="location.name"
          :value="location.id"
        />
      </el-select>

      <div v-if="configError" class="state-block state-block--error">
        {{ configError }}
      </div>
      <div v-else-if="mapError" class="state-block state-block--error">
        {{ mapError }}
      </div>

      <div class="location-list">
        <button
          v-for="location in filteredLocations"
          :key="location.id"
          type="button"
          class="location-item"
          :class="{ active: selectedLocation?.id === location.id }"
          @click="selectLocation(location)"
        >
          <div class="location-item-head">
            <span>{{ location.name }}</span>
            <el-tag size="small" effect="plain">{{ campusTypeLabels[location.type] || '其他' }}</el-tag>
          </div>
          <p>{{ location.address || '暂无地址' }}</p>
          <div class="tag-row">
            <el-tag v-for="tag in location.tags?.slice(0, 3)" :key="tag" size="small" type="info" effect="plain">
              {{ tag }}
            </el-tag>
          </div>
        </button>

        <el-empty v-if="!filteredLocations.length" description="没有匹配的校园地点" />
      </div>
    </section>

    <section class="map-stage">
      <div ref="mapContainer" class="amap-container"></div>

      <div v-if="selectedLocation" class="detail-panel">
        <div class="detail-copy">
          <div class="detail-title">{{ selectedLocation.name }}</div>
          <div class="detail-meta">{{ campusTypeLabels[selectedLocation.type] || '其他' }} · {{ selectedLocation.address }}</div>
          <p>{{ selectedLocation.description }}</p>
        </div>
        <div class="detail-actions">
          <el-button :icon="Aim" @click="focusSelected">定位</el-button>
          <el-button type="primary" :icon="Guide" :loading="routeLoading" @click="planRoute(selectedLocation)">站内路线</el-button>
        </div>
        <div v-if="routeInfo || routeError" class="route-panel" :class="{ 'route-panel--error': routeError }">
          <template v-if="routeInfo">
            <strong>{{ routeInfo.origin?.name || '当前位置' }} → {{ routeInfo.destination?.name || selectedLocation.name }}</strong>
            <span>{{ formatDistance(routeInfo.distance) }} · {{ formatDuration(routeInfo.duration) }}</span>
          </template>
          <template v-else>{{ routeError }}</template>
        </div>
      </div>
    </section>
  </div>
  <AgentFab />
</template>

<script setup>
import AgentFab from '../components/AgentFab.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Aim, Guide, Refresh, Search } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { campusLocationTypes, campusTypeLabels, campusList } from '../data/campusLocations';
import { getAmapConfigError, loadAmap } from '../services/amapService';
import {
  fetchCampusLocations,
  fetchWalkingRoute,
  isRenderableLocation,
  searchCampusLocations
} from '../services/campusLocationService';

const route = useRoute();
const mapContainer = ref(null);
const keyword = ref('');
const activeType = ref('all');
const activeCampus = ref('all');
const campusCenters = {
  nanwangshan: { lng: 114.3955, lat: 30.5173, zoom: 16 },
  future_city: { lng: 114.6140, lat: 30.4580, zoom: 16 },
  all: { lng: 114.5050, lat: 30.4880, zoom: 12 },
};
const campusOptions = computed(() => [
  ...campusList.map(c => ({ label: c.label, value: c.key }))
]);
const locations = ref([]);
const selectedLocation = ref(null);
const loadingLocations = ref(false);
const mapError = ref('');
const configError = ref(getAmapConfigError());
const userPosition = ref(null);
const routeStartId = ref('');
const routeInfo = ref(null);
const routeError = ref('');
const routeLoading = ref(false);

const typeOptions = campusLocationTypes.map((item) => ({ label: item.label, value: item.value }));

let AMapInstance = null;
let map = null;
let infoWindow = null;
let geolocation = null;
let markers = [];
let routeLine = null;

const filteredLocations = computed(() => searchCampusLocations(locations.value, keyword.value, activeType.value, activeCampus.value));

const buildInfoContent = (location) => `
  <div class="campus-info-window">
    <div class="campus-info-title">${location.name}</div>
    <div class="campus-info-meta">${campusTypeLabels[location.type] || '其他'} · ${location.address || '暂无地址'}</div>
    <div class="campus-info-desc">${location.description || '暂无说明'}</div>
    <button type="button" class="campus-info-button" data-location-id="${location.id}">站内路线</button>
  </div>
`;

const clearMarkers = () => {
  markers.forEach(m => m.setMap(null));
  markers = [];
  if (infoWindow) infoWindow.close();
};

const clearRoute = () => {
  routeInfo.value = null;
  routeError.value = '';
  if (map && routeLine) {
    map.remove(routeLine);
  }
  routeLine = null;
};

const renderMarkers = () => {
  if (!map || !AMapInstance) return;
  clearMarkers();

  markers = filteredLocations.value
    .filter(isRenderableLocation)
    .map((location) => {
      const marker = new AMapInstance.Marker({
        position: [location.longitude, location.latitude],
        title: location.name,
        anchor: 'bottom-center',
        clickable: true,
      });
      marker.on('click', (e) => {
        e.stopPropagation?.();
        selectLocation(location);
      });
      marker.setMap(map);
      return marker;
    });

  if (markers.length) {
    if (activeCampus.value !== 'all') {
      const c = campusCenters[activeCampus.value];
      map.setZoomAndCenter(c.zoom, [c.lng, c.lat]);
    } else {
      map.setFitView(markers, false, [80, 80, 80, 80]);
    }
  } else if (activeCampus.value !== 'all') {
    const c = campusCenters[activeCampus.value];
    map.setZoomAndCenter(c.zoom, [c.lng, c.lat]);
  }
};

const openInfoWindow = (location) => {
  if (!map || !AMapInstance || !isRenderableLocation(location)) return;
  if (!infoWindow) {
    infoWindow = new AMapInstance.InfoWindow({ offset: new AMapInstance.Pixel(0, -34) });
  }
  infoWindow.setContent(buildInfoContent(location));
  infoWindow.open(map, [location.longitude, location.latitude]);
  nextTick(() => {
    const button = document.querySelector(`.campus-info-button[data-location-id="${location.id}"]`);
    if (button) {
      button.onclick = () => planRoute(location);
    }
  });
};

const selectLocation = (location) => {
  selectedLocation.value = location;
  if (!map || !isRenderableLocation(location)) return;
  map.setZoomAndCenter(17, [location.longitude, location.latitude]);
  openInfoWindow(location);
};

const focusSelected = () => {
  if (selectedLocation.value) {
    selectLocation(selectedLocation.value);
  }
};

const formatDistance = (meters) => {
  const value = Number(meters || 0);
  if (value >= 1000) return `${(value / 1000).toFixed(1)} 公里`;
  return `${value} 米`;
};

const formatDuration = (seconds) => {
  const value = Number(seconds || 0);
  if (value >= 3600) return `${Math.floor(value / 3600)} 小时 ${Math.round((value % 3600) / 60)} 分钟`;
  return `${Math.max(1, Math.round(value / 60))} 分钟`;
};

const drawRoute = (route) => {
  if (!map || !AMapInstance || !route?.polyline?.length) return;
  if (routeLine) {
    map.remove(routeLine);
  }
  routeLine = new AMapInstance.Polyline({
    path: route.polyline,
    isOutline: true,
    outlineColor: '#ffffff',
    borderWeight: 3,
    strokeColor: '#007aff',
    strokeWeight: 8,
    strokeOpacity: 0.92,
    lineJoin: 'round',
    lineCap: 'round',
    showDir: true
  });
  map.add(routeLine);
  map.setFitView([routeLine, ...markers], false, [90, 90, 90, 90]);
};

const planRoute = async (location) => {
  if (!location || !isRenderableLocation(location)) return;
  routeLoading.value = true;
  routeError.value = '';
  try {
    const params = {
      toId: location.id,
      destination: `${location.longitude},${location.latitude}`,
      destinationName: location.name
    };
    if (routeStartId.value) {
      params.fromId = routeStartId.value;
    } else if (userPosition.value) {
      params.origin = `${userPosition.value.longitude},${userPosition.value.latitude}`;
      params.originName = '当前位置';
    } else {
      throw new Error('请先选择起点，或允许浏览器定位后再规划站内路线。');
    }

    const route = await fetchWalkingRoute(params);
    routeInfo.value = route;
    drawRoute(route);
  } catch (error) {
    clearRoute();
    routeError.value = error.message || '路线规划失败，请稍后再试。';
    ElMessage.warning(routeError.value);
  } finally {
    routeLoading.value = false;
  }
};

const locateUser = () => {
  if (!AMapInstance || !map) return;
  geolocation = new AMapInstance.Geolocation({
    enableHighAccuracy: true,
    timeout: 6000,
    showButton: true,
    showMarker: true,
    showCircle: false,
    position: 'RB'
  });
  map.addControl(geolocation);
  geolocation.getCurrentPosition((status, result) => {
    if (status === 'complete' && result?.position) {
      userPosition.value = {
        longitude: result.position.lng,
        latitude: result.position.lat
      };
    }
  });
};

const initMap = async () => {
  if (configError.value) return;
  try {
    AMapInstance = await loadAmap();
    map = new AMapInstance.Map(mapContainer.value, {
      zoom: 16,
      center: [114.3994, 30.5236],
      viewMode: '2D',
      resizeEnable: true
    });
    map.addControl(new AMapInstance.Scale());
    map.addControl(new AMapInstance.ToolBar({ position: 'RB' }));
    locateUser();
    renderMarkers();
  } catch (error) {
    mapError.value = error.message || '地图加载失败，请检查高德配置或网络。';
  }
};

const loadLocations = async () => {
  loadingLocations.value = true;
  try {
    locations.value = await fetchCampusLocations();
    const locationId = route.query.location;
    routeStartId.value = route.query.from || '';
    selectedLocation.value = locations.value.find((item) => item.id === locationId) || locations.value[0] || null;
    renderMarkers();
    if (selectedLocation.value) {
      selectLocation(selectedLocation.value);
    }
  } finally {
    loadingLocations.value = false;
  }
};

watch([filteredLocations, activeType], () => {
  renderMarkers();
  if (selectedLocation.value && !filteredLocations.value.some((item) => item.id === selectedLocation.value.id)) {
    selectedLocation.value = filteredLocations.value[0] || null;
  }
});

watch(activeCampus, () => {
  if (!map) return;
  selectedLocation.value = null;
  routeInfo.value = null;
  renderMarkers();
});

watch(keyword, () => {
  if (filteredLocations.value.length === 1) {
    selectLocation(filteredLocations.value[0]);
  }
});

onMounted(async () => {
  await loadLocations();
  await initMap();
  if (route.query.route === '1' && selectedLocation.value && routeStartId.value) {
    await nextTick();
    planRoute(selectedLocation.value);
  }
  if (configError.value) {
    ElMessage.error(configError.value);
  }
});

onBeforeUnmount(() => {
  clearRoute();
  clearMarkers();
  if (infoWindow) infoWindow.close();
  if (map) {
    map.destroy();
    map = null;
  }
  geolocation = null;
});
</script>

<style scoped>
.campus-map-page {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  height: 100%;
  min-height: 680px;
  background: #f5f7fb;
}

.map-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  overflow: hidden;
}

.map-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.map-title-row h2 {
  margin: 0;
  color: #1d1d1f;
  font-size: 22px;
}

.map-title-row p {
  margin: 6px 0 0;
  color: #6e6e73;
  font-size: 13px;
}

.search-input {
  flex: 0 0 auto;
}

.type-filter {
  width: 100%;
  overflow-x: auto;
}

.location-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding-right: 2px;
}

.location-item {
  width: 100%;
  padding: 14px;
  text-align: left;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #1d1d1f;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.location-item:hover,
.location-item.active {
  border-color: #007aff;
  box-shadow: 0 8px 22px rgba(0, 122, 255, 0.12);
  transform: translateY(-1px);
}

.location-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 700;
}

.location-item p {
  margin: 8px 0;
  color: #6e6e73;
  font-size: 13px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.map-stage {
  position: relative;
  min-width: 0;
  min-height: 680px;
}

.amap-container {
  width: 100%;
  height: 100%;
  min-height: 680px;
}

.detail-panel {
  position: absolute;
  right: 22px;
  bottom: 22px;
  width: min(420px, calc(100% - 44px));
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(12px);
}

.detail-copy {
  flex: 1 1 220px;
  min-width: 0;
}

.detail-title {
  color: #1d1d1f;
  font-size: 18px;
  font-weight: 800;
}

.detail-meta {
  margin-top: 4px;
  color: #007aff;
  font-size: 13px;
  font-weight: 600;
}

.detail-panel p {
  margin: 8px 0 0;
  color: #4b5563;
  line-height: 1.6;
}

.detail-actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 8px;
}

.route-panel {
  flex: 1 0 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f2f8ff;
  color: #1d1d1f;
  border: 1px solid rgba(0, 122, 255, 0.18);
}

.route-panel strong {
  font-size: 13px;
}

.route-panel span {
  color: #007aff;
  font-size: 13px;
  font-weight: 700;
}

.route-panel--error {
  color: #b42318;
  background: #fff1f0;
  border-color: #ffccc7;
}

.state-block {
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
}

.state-block--error {
  color: #b42318;
  background: #fff1f0;
  border: 1px solid #ffccc7;
}

:global(.campus-info-window) {
  min-width: 220px;
  color: #1d1d1f;
}

:global(.campus-info-title) {
  font-size: 16px;
  font-weight: 800;
}

:global(.campus-info-meta) {
  margin-top: 4px;
  color: #007aff;
  font-size: 12px;
}

:global(.campus-info-desc) {
  margin: 8px 0 12px;
  color: #4b5563;
  line-height: 1.5;
}

:global(.campus-info-button) {
  width: 100%;
  height: 32px;
  border: none;
  border-radius: 7px;
  background: #007aff;
  color: #fff;
  cursor: pointer;
}

@media (max-width: 960px) {
  .campus-map-page {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .map-sidebar {
    max-height: 360px;
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
  }

  .map-stage,
  .amap-container {
    min-height: 520px;
  }

  .detail-panel {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
