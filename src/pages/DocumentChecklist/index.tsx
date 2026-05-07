import { Navigate, useParams } from 'react-router-dom';

/** @deprecated 资料清单已并入「数据整合」，保留路由以兼容旧链接 */
export function DocumentChecklist() {
  const { enterpriseId } = useParams();
  const to = enterpriseId
    ? `/data-integration/${enterpriseId}?tab=checklist`
    : '/data-integration?tab=checklist';
  return <Navigate to={to} replace />;
}
