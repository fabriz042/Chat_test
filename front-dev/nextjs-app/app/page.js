// Simulación de archivo principal de Next.js para SmartPoli
// Normalmente este sería page.tsx o app.tsx en Next.js

import React, { useState, useEffect } from 'react';

// Componentes simulados
const Header = () => (
  <header className="bg-blue-800 text-white p-4">
    <div className="container mx-auto flex justify-between items-center">
      <h1 className="text-2xl font-bold">SmartPoli</h1>
      <nav>
        <ul className="flex space-x-4">
          <li>Dashboard</li>
          <li>Casos</li>
          <li>Oficiales</li>
          <li>Reportes</li>
          <li>Comunicaciones</li>
        </ul>
      </nav>
      <div className="flex items-center space-x-2">
        <span>Oficial López</span>
        <div className="w-8 h-8 bg-blue-600 rounded-full"></div>
      </div>
    </div>
  </header>
);

const Sidebar = () => (
  <aside className="w-64 bg-gray-100 h-screen p-4">
    <h2 className="text-xl font-semibold mb-4">Menú</h2>
    <nav>
      <ul className="space-y-2">
        <li className="p-2 bg-blue-100 rounded">Dashboard</li>
        <li className="p-2 hover:bg-blue-50 rounded">Gestión de Casos</li>
        <li className="p-2 hover:bg-blue-50 rounded">Oficiales</li>
        <li className="p-2 hover:bg-blue-50 rounded">Patrullas</li>
        <li className="p-2 hover:bg-blue-50 rounded">Reportes</li>
        <li className="p-2 hover:bg-blue-50 rounded">Mapas</li>
        <li className="p-2 hover:bg-blue-50 rounded">Chat</li>
        <li className="p-2 hover:bg-blue-50 rounded">Configuración</li>
      </ul>
    </nav>
  </aside>
);

const DashboardCard = ({ title, value, icon, trend }) => (
  <div className="bg-white p-4 rounded-lg shadow">
    <div className="flex justify-between items-center">
      <h3 className="text-gray-500">{title}</h3>
      <span className="text-blue-500">{icon}</span>
    </div>
    <p className="text-2xl font-bold mt-2">{value}</p>
    <p className={`text-sm ${trend > 0 ? 'text-green-500' : 'text-red-500'}`}>
      {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% vs mes anterior
    </p>
  </div>
);

const RecentCases = () => (
  <div className="bg-white p-4 rounded-lg shadow">
    <h3 className="text-lg font-semibold mb-4">Casos Recientes</h3>
    <table className="w-full">
      <thead>
        <tr className="border-b">
          <th className="text-left py-2">ID</th>
          <th className="text-left py-2">Título</th>
          <th className="text-left py-2">Estado</th>
          <th className="text-left py-2">Asignado</th>
        </tr>
      </thead>
      <tbody>
        <tr className="border-b">
          <td className="py-2">CP-2025-042</td>
          <td className="py-2">Robo en tienda</td>
          <td className="py-2"><span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs">En progreso</span></td>
          <td className="py-2">Ofc. Martínez</td>
        </tr>
        <tr className="border-b">
          <td className="py-2">CP-2025-041</td>
          <td className="py-2">Vandalismo</td>
          <td className="py-2"><span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">Resuelto</span></td>
          <td className="py-2">Det. García</td>
        </tr>
        <tr className="border-b">
          <td className="py-2">CP-2025-040</td>
          <td className="py-2">Accidente de tránsito</td>
          <td className="py-2"><span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs">Crítico</span></td>
          <td className="py-2">Sgt. Pérez</td>
        </tr>
        <tr className="border-b">
          <td className="py-2">CP-2025-039</td>
          <td className="py-2">Altercado público</td>
          <td className="py-2"><span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">Nuevo</span></td>
          <td className="py-2">Sin asignar</td>
        </tr>
      </tbody>
    </table>
    <button className="mt-4 text-blue-600 hover:underline">Ver todos los casos</button>
  </div>
);

const ActivityFeed = () => (
  <div className="bg-white p-4 rounded-lg shadow">
    <h3 className="text-lg font-semibold mb-4">Actividad Reciente</h3>
    <div className="space-y-4">
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 bg-blue-600 rounded-full flex-shrink-0"></div>
        <div>
          <p className="text-sm"><span className="font-semibold">Ofc. Martínez</span> actualizó el caso <span className="text-blue-600">CP-2025-042</span></p>
          <p className="text-xs text-gray-500">Hace 5 minutos</p>
        </div>
      </div>
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 bg-green-600 rounded-full flex-shrink-0"></div>
        <div>
          <p className="text-sm"><span className="font-semibold">Det. García</span> cerró el caso <span className="text-blue-600">CP-2025-041</span></p>
          <p className="text-xs text-gray-500">Hace 20 minutos</p>
        </div>
      </div>
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 bg-red-600 rounded-full flex-shrink-0"></div>
        <div>
          <p className="text-sm"><span className="font-semibold">Sistema</span> generó alerta de emergencia en Sector Norte</p>
          <p className="text-xs text-gray-500">Hace 35 minutos</p>
        </div>
      </div>
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 bg-yellow-600 rounded-full flex-shrink-0"></div>
        <div>
          <p className="text-sm"><span className="font-semibold">Sgt. Pérez</span> asignó <span className="text-blue-600">CP-2025-040</span> a equipo de tránsito</p>
          <p className="text-xs text-gray-500">Hace 45 minutos</p>
        </div>
      </div>
    </div>
    <button className="mt-4 text-blue-600 hover:underline">Ver toda la actividad</button>
  </div>
);

const MapView = () => (
  <div className="bg-white p-4 rounded-lg shadow">
    <h3 className="text-lg font-semibold mb-4">Mapa de Incidentes</h3>
    <div className="bg-gray-200 h-64 rounded flex items-center justify-center">
      [Mapa de la ciudad con incidentes marcados]
    </div>
    <div className="mt-4 flex space-x-2">
      <button className="text-sm bg-blue-600 text-white px-3 py-1 rounded">Ver mapa completo</button>
      <button className="text-sm border border-blue-600 text-blue-600 px-3 py-1 rounded">Filtrar</button>
    </div>
  </div>
);

// Página principal
const DashboardPage = () => {
  const [stats, setStats] = useState({
    casosActivos: 42,
    oficiales: 23,
    emergencias: 5,
    respuesta: '18 min'
  });

  // Simulación de carga de datos
  useEffect(() => {
    // Simular una llamada API
    const timer = setTimeout(() => {
      setStats({
        casosActivos: 42,
        oficiales: 23,
        emergencias: 5,
        respuesta: '18 min'
      });
    }, 1000);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
          
          {/* Estadísticas */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <DashboardCard 
              title="Casos Activos" 
              value={stats.casosActivos} 
              icon="📁" 
              trend={-5} 
            />
            <DashboardCard 
              title="Oficiales de Servicio" 
              value={stats.oficiales} 
              icon="👮" 
              trend={+2} 
            />
            <DashboardCard 
              title="Emergencias Activas" 
              value={stats.emergencias} 
              icon="🚨" 
              trend={+10} 
            />
            <DashboardCard 
              title="Tiempo Medio Respuesta" 
              value={stats.respuesta} 
              icon="⏱️" 
              trend={-12} 
            />
          </div>
          
          {/* Contenido principal */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <RecentCases />
            <ActivityFeed />
          </div>
          
          {/* Mapa */}
          <MapView />
        </main>
      </div>
    </div>
  );
};

export default DashboardPage;
