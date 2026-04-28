import { GetStaticProps } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import PrivacyPolicy from '../components/PrivacyPolicy';

export default function PrivacyPage() {
  return <PrivacyPolicy />;
}

export const getStaticProps: GetStaticProps = async ({ locale }) => {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? 'en', [
        'common',
        'footer',
      ])),
    },
  };
};
