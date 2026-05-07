import AMapLoader from '@amap/amap-jsapi-loader';

const AMAP_PLUGINS = [
  'AMap.Scale',
  'AMap.ToolBar',
  'AMap.Geolocation',
  'AMap.PlaceSearch',
  'AMap.Walking'
];

let amapPromise = null;

export const getAmapConfigError = () => {
  if (!import.meta.env.VITE_AMAP_KEY) return '未配置 VITE_AMAP_KEY，无法加载高德地图。';
  if (!import.meta.env.VITE_AMAP_SECURITY_CODE) return '未配置 VITE_AMAP_SECURITY_CODE，无法加载高德地图。';
  return '';
};

export const loadAmap = () => {
  const configError = getAmapConfigError();
  if (configError) {
    return Promise.reject(new Error(configError));
  }

  window._AMapSecurityConfig = {
    securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE
  };

  if (!amapPromise) {
    amapPromise = AMapLoader.load({
      key: import.meta.env.VITE_AMAP_KEY,
      version: '2.0',
      plugins: AMAP_PLUGINS
    });
  }

  return amapPromise;
};
