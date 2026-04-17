import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import os

# --- LISTE COMPLÈTE DES SÉNATEURS (880+ IDs) ---
senateurs_ids = [
    "adam_gabriel1595r3", "aguillon_louis1636r3", "alheritiere_henri0651r3", "allegre_vincent0697r3",
    "allemand_clement0512r3", "amic_jean0117r3", "andrieu_edouard1688r3", "anne_norbert0334r3",
    "arago_emmanuel1087r3", "arbel_lucien1344r3", "armbruster_raymond0231r3", "arnaudeau_eugene1758r3",
    "astier_marcel0136r3", "astier_placide0139r3", "astor_joseph0814r3", "auber_joseph0851r3",
    "audiffred_jean_honore1321r3", "audren_de_kerdrel_vincent0893r3", "auray_charles1351r3",
    "babaud_lacroze_leonide0398r3", "bachelet_alexandre1563r3", "baduel_albert0360r3",
    "baillardel_de_lareinty_henri1271r3", "barbey_edouard1693r3", "barbier_andre1813r3",
    "barne_henry0321r3", "barthe_marcel1046r3", "barthou_louis1071r3", "bassinet_athanase1557r3",
    "batbie_anselme0151r3", "baudin_pierre0016r3", "baufle_maurice0680r3", "bazile_gaston0835r3",
    "bazire_elphege1045r3", "beaumont_jean0050r3", "beaupin_francois1237r3", "belle_antoine0299r3",
    "bels_adrien0083r4", "benard_leonus0852r3", "beral_eloi0609r3", "berard_alexandre0019r3",
    "berard_leon1053r3", "berenger_henry0845r3", "bergeon_benoit0324r3", "berger_pierre0378r3",
    "bernard_jean0686r3", "bernot_achille1669r3", "bersez_paul1400r3", "berthoulat_georges1656r3",
    "bertrand_williams0414r3", "besnard_rene0300r3", "betfert_jean0589r3", "betoulle_leon1788r3",
    "bezine_paul1849r3", "bidault_charles0308r3", "bienvenu_martin_jean_baptiste1840r3",
    "bire_alfred1744r3", "bisseuil_eugene0418r3", "bizot_de_fonteny_pierre0864r3",
    "blaignan_raymond0104r3", "blanc_philippe1324r3", "bluysen_paul1835r3", "bocher_pierre0344r3",
    "bodinier_guillaume1159r3", "boivin_champeaux_jean0407r4", "bollet_donat0013r3",
    "bompard_maurice0711r3", "bon_leon0314r3", "bonnefille_frederic1664r3",
    "bonnefoy_sibour_georges0827r3", "bonnelat_emile0439r3", "boret_victor1774r3",
    "borne_charles0678r3", "bosc_jean0822r3", "boudenoot_louis0930r3", "bouffier_albert1134r3",
    "bougere_ferdinand1163r3", "bouguen_yves0594r3", "bougues_victor0094r3", "bouilliez_ferdinand0940r3",
    "boulanger_ernest1019r3", "bourdeaux_henry1685r3", "bourganel_pierre1360r3", "bourgeat_louis1724r3",
    "bourgeois_joseph1110r3", "bourgeois_leon0647r3", "bouvart_paul0778r3", "bozerian_jules0374r3",
    "brager_de_la_ville_moysan_eugene0529r3", "brard_mathurin0917r3", "breton_andre0447r3",
    "briens_ernest1030r3", "brindeau_louis1617r3", "brocard_maximin0452r3", "brossard_etienne1319r3",
    "bruel_eugene0042r3", "brugnot_alfred1798r3", "bruguier_georges0829r3", "brun_charles1729r3",
    "brunet_arthur0277r3", "buhan_eugene0218r3", "bussiere_etienne0457r3", "buvignier_jean1022r3",
    "cabart_danneville_charles_maurice1036r3", "cabart_danneville_maurice1042r3",
    "cadilhon_charles0345r3", "caduc_armand0216r3", "caillaux_joseph1254r3", "caillier_rene0196r3",
    "calmel_armand0209r3", "calvet_auguste0412r3", "camparan_victor0101r3", "canrobert_francois0394r3",
    "capus_joseph0215r3", "carre_bonvalet_rene0423r3", "carrere_gaston0762r3",
    "casabianca_de_paul1854r3", "cassez_emile0867r3", "castillard_henri0222r3",
    "catalogne_jacques1059r3", "cautru_camille0339r3", "cauvin_ernest1658r3", "cavillon_edmond1697r3",
    "cazelles_jean0828r3", "chabert_charles0722r3", "chaix_cyprien0074r3", "chalamet_henri0144r3",
    "chalamet_jean0131r3", "challemel_lacour_paul0315r3", "chambonnet_auguste0629r3",
    "champetier_de_ribes_auguste0517r4", "chanal_jean0017r3", "chantagrel_jean0998r3",
    "chantemille_joseph0047r3", "chapsal_fernand0417r3", "charabot_eugene0118r3",
    "chardon_alfred1311r3", "charmes_francis0370r3", "charpentier_leon0163r3", "charton_edouard1837r3",
    "chassaing_eugene0995r3", "chastenet_de_castaing_guillaume0201r3", "chaumet_jean0195r3",
    "chaumie_joseph0747r3", "chaumontel_louis1306r3", "chautemps_alphonse0309r3",
    "chautemps_emile1313r3", "chauveau_claude0544r3", "chauveau_franck0884r3",
    "chaver_biere_leonce0466r3", "chenebenoit_leon0038r3", "cheron_henry0337r3", "chevalier_pol1014r3",
    "chiris_francois0121r3", "chopin_emile1231r3", "chovet_alphonse0889r3", "ciceron_adolphe0844r3",
    "claeys_leon1385r3", "clamamus_jean_marie1568r3", "claude_nicolas1796r3", "claveille_albert0663r3",
    "clemenceau_georges1741r3", "clement_leon0258r3", "clementel_etienne1006r3", "cochard_philibert1222r3",
    "cochery_adolphe0505r3", "cocula_jean0604r3", "codet_jean1786r3", "combes_emile0416r3",
    "combescure_jean0243r3", "comte_d_alsace_thierry1812r3", "constans_ernest0107r3",
    "converset_rene0226r3", "cordelet_louis1239r3", "cornet_lucien1850r3", "cornil_andre0053r3",
    "cornudet_des_chaumettes_honore1635r3", "cosnier_henri0280r3", "coste_gustave1838r3",
    "coucoureux_joseph0296r3", "courcel_alphonse_chodron_de1653r3", "courregelongue_marcel0213r3",
    "couteaux_aristide1764r3", "couturier_jean1185r3", "couyba_charles1178r3", "coyrard_jean0408r3",
    "cremieux_fernand0821r3", "crepin_felix0850r3", "cuminal_isidore0140r3", "curral_hippolyte1322r3",
    "cuttoli_paul0695r3", "cuvinot_paul0878r3", "d_andlau_de_hombourg_hubert1107r3",
    "d_andlau_joseph0888r3", "d_aunay_charles1263r3", "d_estournelles_de_constant_paul1252r3",
    "d_harcourt_charles0350r3", "d_osmoy_charles0755r3", "damecour_emile1047r3",
    "danelle_bernardin_jean0870r3", "daniel_vincent_charles1382r3", "daraignez_ernest0341r3",
    "darbot_jean0873r3", "daude_gleize_paulin0860r3", "dauphin_albert1648r3", "dauphinot_jean0637r3",
    "dauthy_henry0275r3", "dauzier_louis0363r3", "david_fernand1309r3", "de_bejarry_amedee1748r3",
    "de_bertier_de_sauvigny_jean_marie0704r3", "de_blois_georges1060r3", "de_blois_louis1075r3",
    "de_bondy_francois0261r3", "de_breil_de_pontbriand_fernand1284r3",
    "de_bremond_d_ars_guillaume0388r3", "de_carne_henri0565r3", "de_castellane_stanislas0375r3",
    "de_ces_caupenne_louis0349r3", "de_chammard_jacques0464r3", "de_champagny_henri0569r3",
    "de_cornulier_de_la_lande_auguste1747r3", "de_courtois_pierre0063r3", "de_cuverville_jules0800r3",
    "de_dion_albert1292r3", "de_flers_alfred0914r3", "de_fontaines_raymond1746r3",
    "de_gavardie_henri0342r3", "de_goulaine_geoffroy0906r3", "de_guibourg_de_luzinais_ernest1282r3",
    "de_kerguezec_gustave0567r3", "de_la_batut_ferdinand0668r3", "de_la_grange_amaury1389r3",
    "de_la_jaille_charles1272r3", "de_la_monneraye_charles0900r3", "de_la_sicotiere_pierre0895r3",
    "de_lacroix_de_ravignan_marie0335r3", "de_ladmirault_louis1763r3", "de_lamarzelle_gustave0902r3",
    "de_landemont_ambroise1273r3", "de_las_cases_emmanuel0855r3", "de_lavrignais_alexandre1279r3",
    "de_lavrignais_henri1754r3", "de_leusse_jean1109r3", "de_lubersac_louis0034r3",
    "de_ludre_frolois_rene0897r3", "de_lur_saluces_thomas0192r3", "de_maille_de_la_jumelliere_armand1160r3",
    "de_marguerie_henri0709r3", "de_montaigu_pierre1277r3", "de_montfort_louis1574r3",
    "de_monti_de_reze_henri0960r3", "de_monzie_anatole0605r3", "de_moustier_rene0688r3",
    "de_pavin_de_lafarge_henri0145r3", "de_pomereu_michel1598r3", "de_raismes_arnold0804r3",
    "de_remusat_paul0078r3", "de_rothschild_maurice0087r3", "de_rouge_olivier1067r3",
    "de_roziere_eugene0858r3", "de_saint_germain_adolphe0559r3", "de_saint_pierre_louis0352r3",
    "de_saint_vallier_charles0032r3", "de_saulces_de_freycinet_louis1713r3", "de_selves_justin1727r3",
    "de_treveneuc_henri0575r3", "de_treveneuc_robert0572r3", "de_verninac_saint_maur_henri0603r3",
    "de_wendel_guy0706r3", "deandreis_elisee0249r3", "debierre_charles1406r3", "decauville_paul1626r3",
    "decrais_albert0207r3", "decroix_adolphe1287r3", "decroze_georges0886r3", "deffis_armand1077r3",
    "defumade_alphonse0619r3", "dehove_joseph1380r3", "delahaye_dominique1161r3",
    "delahaye_jules1154r3", "delcros_elie1088r3", "delesalle_charles0979r3", "delhoume_louis0401r3",
    "dellestable_antoine0462r3", "delobeau_louis0784r3", "deloncle_charles1374r3",
    "delpech_auguste0187r3", "delpierre_casimir0891r3", "delpuech_vincent000685", "delsol_jean0292r3",
    "delthil_roger0436r4", "demellier_louis1641r3", "demole_charles1218r3", "denis_gustave0956r3",
    "denoix_arnaud0671r3", "dentu_georges0920r3", "depreux_theophile1399r3", "deprez_louis0925r3",
    "desjardins_charles0031r3", "desmazes_joseph0696r3", "desmons_frederic0832r3",
    "destieux_junca_paul0156r3", "develle_edmond1012r3", "deves_paul0369r3", "diancourt_louis0634r3",
    "diebolt_weber_michel1104r3", "donnet_jules1789r3", "donon_marcel0508r3", "doumer_paul0473r3",
    "doumergue_gaston0833r3", "drivet_antoine1373r3", "dron_gustave1388r3", "drouhet_theodore0848r3",
    "drumel_etienne0172r3", "du_motier_de_la_fayette_edmond0511r3", "dubost_antonin1187r3",
    "duboys_fresney_etienne0952r3", "duchein_fabien0088r3", "duchesne_fournet_paul0346r3",
    "dudouyt_pierre1037r3", "dufay_jean0382r3", "dufoussat_jean_baptiste0624r3", "dumesnil_antoine0497r3",
    "dumesnil_jacques1613r3", "dumont_charles0432r3", "duplantier_raymond1761r3", "dupouy_bernard0198r3",
    "duprey_georges1215r3", "dupuy_charles0513r3", "dupuy_jean1084r3", "dupuy_paul1085r3",
    "durand_jean0270r3", "durand_savoyat_leonce1197r3", "duroux_jacques0840r3", "dusolier_alcide0667r3",
    "duval_cesar1318r3", "eccard_frederic1102r3", "elby_jules0935r3", "elva_christian0958r3",
    "enjolras_francisque0518r3", "ermant_georges0030r3", "espivent_de_la_villeboisnet_henry1275r3",
    "even_pierre0579r3", "eymard_duvernay_joseph1190r3", "eymery_bernard0672r3", "eynard_francois0724r3",
    "fabry_jean0685r3", "fagot_eugene0162r3", "faisans_armand1069r3", "fallieres_armand0754r3",
    "farines_achille1095r3", "farjon_roger0971r3", "faure_joseph0463r3", "faure_maurice0716r3",
    "fayard_joseph0721r3", "faye_etienne0733r3", "fayolle_joseph0598r3", "fenoux_maurice0817r3",
    "feral_louis0106r3", "feray_ernest1643r3", "ferrand_camille0621r3", "ferrouillat_jean_baptiste1735r3",
    "fevre_achille1781r3", "flaissieres_simeon0329r3", "flandin_etienne1832r3", "flayelle_maurice1800r3",
    "fleury_paul0896r3", "folliet_andre1312r3", "fontanille_rene0614r3", "forest_charles1300r3",
    "forichon_emile0279r3", "fortier_edouard1596r3", "fortin_jules0810r3", "foucher_octave0306r3",
    "fougeirol_edouard0132r3", "fouilloux_albert0014r3", "fourcade_manuel1086r3", "fourment_gustave1742r3",
    "fousset_ernest0498r3", "francois_saint_maur_charles1294r3", "francoz_felix1307r3",
    "frery_charles1816r3", "fresneau_armand0905r3", "frezoul_paul0182r3", "frogier_de_ponlevoy_paul1811r3",
    "froment_louis1678r3", "fruchier_lazare0067r3", "gabrielli_thadee0481r3", "gacon_jules0043r3",
    "gadaud_antoine0660r3", "gadaud_felix0673r3", "gaillard_gilbert0997r3", "gailly_gustave0167r3",
    "gallet_claudius1314r3", "gallini_jean_francois0492r3", "galtier_jean0238r3", "gardey_abel0150r3",
    "garnier_paul0557r3", "garran_de_balzan_francois1634r3", "garrigou_louis0606r3",
    "garrisson_gustave1723r3", "gasnier_duparc_alphonse0563r3", "gaudaire_gaston1851r3",
    "gaudin_de_villaine_adrien1041r3", "gaudineau_baptiste1743r3", "gaudy_felix0676r3",
    "gautherot_gustave1274r3", "gauthier_armand0264r3", "gautron_jacques0774r3", "gauvin_eusebe0384r3",
    "gay_de_savary_hippolyte1696r3", "gayot_emile0221r3", "gegauff_sebastien1117r3", "genet_georges0420r3",
    "genoux_prachee_victor1171r3", "gent_alphonse1701r3", "gentilliez_charles0037r3",
    "george_eustache1808r3", "gerard_albert0168r3", "gerente_paul0838r3", "giacobbi_paul0474r3",
    "giguet_honore0009r3", "gilbert_boucher_charles1651r3", "gilbert_raymond0781r3", "giordan_joseph0494r3",
    "girard_alfred1403r3", "girard_theodore1638r3", "girault_jean0426r3", "giresse_edouard0736r3",
    "godart_justin1138r3", "godin_jules1831r3", "goirand_andre1629r3", "goirand_leopold1625r3",
    "gomot_hippolyte0986r3", "goujon_etienne0018r3", "gounin_rene0402r3", "gourju_antonin1136r3",
    "goutant_charles0174r3", "goy_emile1320r3", "grand_alfred0620r3", "gravin_francois1296r3",
    "grevy_paul0427r3", "griffe_charles0248r3", "grimaud_joseph0083r3", "grivart_louis0525r3",
    "grosdidier_auguste1025r3", "grosjean_alexandre0687r3", "guerin_eugene1709r3", "guesnier_maurice1633r3",
    "guichard_jules1842r3", "guiffrey_georges0073r3", "guilhem_jacques0271r3", "guillemaut_charles1213r3",
    "guillemaut_lucien1225r3", "guillemot_yves0787r3", "guillier_pierre0656r3", "guillois_louis0898r3",
    "guilloteaux_jean0909r3", "guindey_anatole0737r3", "guinot_charles0298r3", "guyot_emile1127r3",
    "guyot_lavaline_jean_baptiste0992r3", "hachette_rene0035r3", "halgan_emmanuel1753r3",
    "halgan_stephane1752r3", "halna_du_fretay_francois0813r3", "halna_du_fretay_hyppolite0783r3",
    "hamelin_henri1847r3", "hannotin_edmond0165r3", "haugoumar_des_portes_charles0576r3",
    "haulon_seraphin1068r3", "hayez_paul1415r3", "hebrard_adrien0092r3", "helmer_paul1114r3",
    "hennessy_james0392r3", "herisson_sylvestre1236r3", "hervey_maurice0758r3", "hery_rene1637r3",
    "hirschauer_auguste0707r3", "honnorat_andre0070r3", "hubert_lucien0176r3", "hugo_victor1354r3",
    "hugot_louis0531r3", "huguet_auguste0972r3", "humblot_emile0871r3", "huon_de_penanster_charles0571r3",
    "isaac_pierre0843r3", "israel_alexandre0223r3", "jacques_remy1822r3", "jacquier_paul1310r3",
    "jametel_gustave1667r3", "jamin_eugene0967r3", "japy_frederic1817r3", "japy_gaston0684r3",
    "jenouvrier_leon0560r3", "jobard_louis1175r3", "join_lambert_andre0759r3", "jonnart_celestin0975r3",
    "josse_prosper0745r3", "jossot_pierre0554r3", "joubert_bonnaire_achille1156r3",
    "jouffrault_camille1624r3", "jouffray_camille1192r3", "journault_louis1660r3",
    "jouvenel_des_ursins_henri0468r3", "jovelet_anatole1661r3", "judet_victor0628r3",
    "kiener_christian1803r3", "klotz_louis1683r3", "knight_amedee0700r3", "labbe_leon0918r3",
    "labiche_emile0771r3", "labiche_jules1040r3", "laboulbene_georges0740r3", "labrousse_francois0002r4",
    "labrousse_philippe0456r3", "lacave_laplagne_louis0128r3", "lacombe_bertrand0390r3",
    "laffont_paul0184r3", "lafond_de_saint_mur_guy0455r3", "lancien_ferdinand0803r3",
    "landrodie_pierre0421r3", "laporte_edouard0750r3", "latappy_arthur0340r3", "laudier_henri0442r3",
    "lauraine_jean_octave0422r3", "laurens_paul0728r3", "lautier_pierre1861r3", "lauvray_leon0752r3",
    "laval_pierre1565r3", "lavergne_bernard1682r3", "lavergne_fernand1695r3", "lavertujon_andre0205r3",
    "lavoinne_andre1612r3", "le_bail_georges0793r3", "le_breton_paul0954r3", "le_chevalier_georges1247r3",
    "le_cour_grandmaison_charles1288r3", "le_cour_grandmaison_henri1289r3", "le_gorgeu_victor0818r3",
    "le_guay_leon1073r3", "le_guen_edouard0796r3", "le_hars_theodore0792r3", "le_jeune_olivier0788r3",
    "le_moignic_eugene1836r3", "le_monnier_pierre1250r3", "le_provost_de_launay_louis0584r3",
    "le_roux_paul1745r3", "le_troadec_paul0586r3", "lebert_andre1248r3", "leblanc_edmond0970r3",
    "lebrun_albert0945r3", "lecler_pierre0631r3", "lecointe_alphonse0735r3", "lecomte_maxime1379r3",
    "lecourtier_georges1026r3", "lederlin_paul0496r3", "lefebvre_du_prey_edmond0976r3",
    "lefevre_abel0761r3", "lefevre_alexandre1371r3", "leglos_joseph0273r3", "legludic_prosper1251r3",
    "legrand_gery1408r3", "leguet_firmin0170r3", "lelievre_adolphe0450r3", "lemarie_louis0562r3",
    "lemery_henry0701r3", "leneveu_robert0908r3", "lenoel_emile1029r3", "leporche_alphonse1246r3",
    "leroux_aime0036r3", "leydet_victor0316r3", "leygue_honore0095r3", "lhopiteau_gustave0772r3",
    "libert_marcel0916r3", "limouzain_laplanche_pierre0400r3", "lintilhac_eugene0361r3",
    "linyer_louis1278r3", "lisbonne_emile0723r3", "lissar_jean1061r3", "loubat_pierre1698r3",
    "loubet_emile0714r3", "loubet_joseph0625r3", "louis_dreyfus_louis0119r3", "lourties_victor0343r3",
    "lucet_jacques0690r3", "lugol_georges1591r3", "macherez_alfred0029r3", "machet_georges1302r3",
    "madignier_pierre1359r3", "magnien_gabriel1229r3", "magny_paul1561r3", "maillard_augustin1276r3",
    "malezieux_francois0025r3", "mallarme_andre0841r3", "malsang_paul1001r3", "manceau_anatole1155r3",
    "mando_eugene0573r3", "maquennehen_alfred1650r3", "maret_paul1644r3", "marion_de_faverges_joseph1196r3",
    "maroger_jean0200r4", "marquis_henri0938r3", "marraud_pierre0748r3", "martell_edouard0399r3",
    "martin_binachon_regis0514r3", "martin_felix1214r3", "martin_louis1739r3", "martinet_antony0428r3",
    "mascuraud_alfred1564r3", "mathey_alfred1208r3", "mauger_hippolyte0446r3", "maureau_achille1704r3",
    "mayran_casimir0282r3", "maze_hippolyte1652r3", "mazeau_charles0538r3", "maziere_pierre0644r3",
    "medecin_jean0127r3", "meinadier_pierre0819r3", "mejan_louis0834r3", "meline_jules1799r3",
    "menier_gaston1610r3", "mercier_auguste1293r3", "mercier_jean0006r3", "meric_victor1732r3",
    "merlet_jules1074r3", "merlin_charles1398r3", "merlin_fernand1341r3", "messimy_adolphe0021r3",
    "messner_ernest0552r3", "mezieres_alfred0932r3", "michal_ladichere_francois1183r3",
    "michaut_henri0948r3", "michaux_hubert0698r3", "michel_henri0069r3", "michel_louis0933r3",
    "michel_marcel0657r3", "michel_pierre0568r3", "milan_francois1305r3", "milhet_fontarabie_jean0847r3",
    "millaud_edouard1120r3", "millerand_alexandre0910r3", "milliard_victor0760r3",
    "millies_lacroix_raphael0351r3", "mir_eugene0269r3", "moinet_jean0405r3", "mollard_maurice1297r3",
    "monestier_clement0859r3", "monfeuillart_ernest0635r3", "monis_ernest0193r3", "monnier_leon0742r3",
    "monsservin_emile0283r3", "monsservin_joseph0284r3", "montesquiou_fezensac_philippe0152r3",
    "mony_louis0230r3", "morand_maurice1749r3", "morel_hippolyte1043r3", "morel_jean_baptiste1326r3",
    "morellet_hippolyte0012r3", "morizet_andre1567r3", "moroux_alfred0263r3", "mounie_auguste1331r3",
    "mourier_louis0823r3", "mulac_auguste0397r3", "muller_eugene1101r3", "munier_louis1133r3",
    "muracciole_ange0487r3", "neron_edouard0523r3", "ninard_jean_baptiste1783r3", "nioche_pierre0304r3",
    "noel_charles0885r3", "obissier_louis0200r3", "ollivier_auguste0590r3", "ordinaire_maurice0679r3",
    "ostermann_paul1118r3", "oudet_alexandre0681r3", "ournac_camille0079r3", "ouvrier_antoine0287r3",
    "palmade_maurice0409r3", "pams_jules1089r3", "parent_nicolas1299r3", "paris_auguste0921r3",
    "parisot_louis1804r3", "parissot_albert0757r3", "pasquet_louis0313r3", "pauliac_joseph0617r3",
    "pauliat_louis0443r3", "pazat_louis0338r3", "peaudecerf_valentin0434r3", "pedebidou_adolphe1079r3",
    "pelisse_paul0240r3", "pelissier_felix0863r3", "pelletier_jean1228r3", "penancier_eugene1605r3",
    "penicaud_rene1784r3", "perchot_justin0062r3", "perdrix_henri0730r3", "peres_eugene0189r3",
    "pernot_georges0335r4", "peronne_louis0160r3", "perras_jean_claude1141r3", "perreau_gustave0413r3",
    "perrier_antoine1304r3", "perrier_leon1193r3", "petit_frederic1677r3", "petitjean_claude1221r3",
    "petitjean_victor1267r3", "peyrat_alphonse1369r3", "peyronnet_albert0055r3", "peyrot_jean0662r3",
    "peytral_paul0322r3", "peytral_victor0076r3", "philip_jean0155r3", "philipot_anatole0532r3",
    "pichery_pierre0386r3", "pichon_louis0791r3", "pichon_stephen0429r3", "pierrin_amedee1673r3",
    "pieyre_marius0448r3", "pin_joseph1707r3", "pinault_eugene0540r3", "piot_edme0550r3",
    "pitti_ferrandi_francois0477r3", "pitti_ferrandi_francois0484r3", "plaisant_marcel0005r4",
    "pochon_joseph0015r3", "poincare_raymond1024r3", "poirrier_alfred0641r3", "poirrier_francois1358r3",
    "poirson_henri1646r3", "ponthier_de_chamaillard_henri0809r3", "poriquet_charles0901r3",
    "porquier_adolphe0815r3", "porteu_andre0542r3", "potie_auguste1410r3", "poulle_guillaume1765r3",
    "pradal_victor0138r3", "presseq_leopold1720r3", "prevet_charles1608r3",
    "provost_dumarchais_gaston1269r3", "queinnec_jacques0794r3", "quesnel_louis1575r3",
    "queuille_henri0469r3", "rabier_fernand0501r3", "rajon_claude1188r3", "rambaud_joseph0190r3",
    "rambaud_louis1750r3", "rambourgt_eugene0229r3", "ranson_auguste1566r3", "ratier_antony0259r3",
    "raymond_leon1779r3", "raynaud_clement0278r3", "razimbaud_jules0239r3", "reboul_camille0252r3",
    "regismanset_jacques1588r3", "regnier_marcel0044r3", "renaudat_alphonse0232r3",
    "revillon_michel0022r3", "rey_edouard1191r3", "reymond_emile1338r3", "reymond_francisque1336r3",
    "reynald_georges0183r3", "reynaud_joseph0717r3", "ribiere_hippolyte1841r3", "ribiere_marcel1846r3",
    "ribot_alexandre0941r3", "richard_adrien1807r3", "richard_jean1211r3", "rillard_de_verneuil_henri0040r3",
    "ringot_francois0974r3", "rio_alphonse0903r3", "riotteau_emile1031r3", "riou_charles0894r3",
    "rivet_gustave1198r3", "robert_dehault_louis0868r3", "robert_pierre1327r3", "robert_pierre1590r3",
    "robin_charles0011r3", "roche_edouard0134r3", "roger_jean0655r3", "roland_leon0879r3",
    "rolland_camille1131r3", "rolland_leon1715r3", "rouby_hippolyte0467r3", "rouland_julien1587r3",
    "roussel_edouard1407r3", "roussel_emile0027r3", "roussel_theophile0853r3", "roustan_marius0246r3",
    "rouvier_paul0406r3", "roux_freissineng_pierre1827r3", "royneau_albert0777r3", "rozier_felix0719r3",
    "sabaterie_pierre_jean0994r3", "saillard_albin0682r3", "saint_germain_marcel1823r3",
    "saint_prix_oscar0141r3", "saint_quentin_louis0355r3", "saint_romme_mathias1205r3",
    "salmon_alfred0977r3", "salneuve_mathieu0996r3", "sari_emile0482r3", "sarraut_albert0265r3",
    "sarraut_maurice0276r3", "sauvan_honore0123r3", "savignol_simon0111r3", "schrameck_abraham0319r3",
    "sclafer_james0169r4", "sebire_auguste1035r3", "sebline_charles0033r3", "serre_louis1705r3",
    "servain_henri0592r3", "servant_jacques1772r3", "signard_maurice1168r3", "simonet_hippolyte0626r3",
    "sireyjol_leon0664r3", "soubigou_francois0789r3", "soulie_louis1355r3", "soustre_marius0057r3",
    "spuller_eugene0548r3", "steeg_theodore1554r3", "stourm_charles0545r3", "strauss_paul1334r3",
    "stuhl_jean0708r3", "surreaux_victor1760r3", "tamisier_francois0425r3", "tassin_pierre0376r3",
    "tasso_henri0331r3", "teisserenc_de_bort_edmond1790r3", "teisserenc_de_bort_pierre1775r3",
    "tezenas_antoine0228r3", "theret_edmond0951r3", "thezard_leopold1759r3", "thiery_laurent1819r3",
    "thorel_jules0739r3", "thoumyre_robert1579r3", "thounens_albert0217r3", "thuillier_alfred1559r3",
    "thurel_jules0437r3", "tillaye_louis0336r3", "tissier_louis1710r3", "tolain_henri1332r3",
    "tournan_isidore0158r3", "touron_eugene0026r3", "toy_riont_maurice0081r3", "trarieux_ludovic0212r3",
    "trystram_jean_baptiste1413r3", "turgis_hippolyte0354r3", "turlier_henri1232r3",
    "ulmo_georges0872r3", "vagnat_charles0075r3", "valadier_jean0770r3", "valette_desire0718r3",
    "valle_ernest0643r3", "vallier_germain1140r3", "vallier_joseph1201r3", "varroy_henry0928r3",
    "velten_geoffroy0311r3", "veron_auguste0527r3", "veyssiere_gaston1589r3",
    "vidal_de_saint_urbain_gabriel0294r3", "viellard_louis1820r3", "viellard_migeon_francois1815r3",
    "vieu_louis1694r3", "vigarosy_jean_baptiste0185r3", "viger_albert0500r3", "vilar_edouard1097r3",
    "villard_ferdinand0618r3", "villault_duchesnois_jean1032r3", "ville_pierre0048r3",
    "vincent_emile0534r3", "vinet_louis0767r3", "viseur_jules0959r3", "vissaguet_ernest0517r3",
    "volland_francois0931r3", "waddington_richard1606r3", "waddington_william0028r3",
    "waldeck_rousseau_pierre1368r3", "weiller_jean1106r3"
]


def scrape_senator_safe(s_id):
    url = f"https://www.senat.fr/senateur-3eme-republique/{s_id}.html"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200: return []

        soup = BeautifulSoup(r.content, "html.parser")
        text = " ".join(soup.get_text().split())

        h1 = soup.find("h1")
        nom = h1.get_text(strip=True) if h1 else s_id

        # 1. Capture Elections
        starts = re.findall(r"(?:Elu|Réélu) (?:le|du) ([\d\w\s]+? \d{4})", text, re.IGNORECASE)

        # 2. Capture Fin de Mandat (Stricte)
        # Priorité 1 : Fin de mandat explicite
        end_match = re.search(r"Fin de mandat le ([\d\w\s]+? \d{4})", text, re.IGNORECASE)

        if end_match:
            final_date = end_match.group(1).strip()
        else:
            # Priorité 2 : Décès contextuel (seulement si "en cours de mandat")
            death_in_mandate = re.search(r"Décédé le ([\d\w\s]+? \d{4}).*?en cours de mandat", text, re.IGNORECASE)
            if death_in_mandate:
                final_date = death_in_mandate.group(1).strip()
            else:
                final_date = "Non spécifiée"

        results = []
        for i, start_date in enumerate(starts):
            if i == len(starts) - 1:
                m_to = final_date
            else:
                m_to = f"Réélu le {starts[i + 1]}"

            results.append({
                "senat_id": s_id,
                "nom": nom,
                "mandat_start": start_date,
                "mandat_end": m_to
            })
        return results
    except Exception as e:
        print(f"Error for {s_id}: {e}")
        return []


# --- EXECUTION ---
OUTPUT_FILE = "senateurs_complets_final_fixed.csv"
all_data = []

print(f"🚀 Lancement du scraping final pour {len(senateurs_ids)} sénateurs...")

for i, s_id in enumerate(senateurs_ids):
    data = scrape_senator_safe(s_id)
    all_data.extend(data)

    # Sauvegarde intermédiaire toutes les 20 lignes
    if (i + 1) % 20 == 0:
        print(f"📈 Progress: {i + 1}/{len(senateurs_ids)}")
        pd.DataFrame(all_data).to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    time.sleep(0.3)  # Protection contre le ban IP

# Sauvegarde Finale
df_final = pd.DataFrame(all_data)
df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

print(f"\n✅ TERMINÉ !")
print(f"📂 Fichier disponible : {os.path.abspath(OUTPUT_FILE)}")
print(f"📊 {len(df_final)} mandats extraits au total.")